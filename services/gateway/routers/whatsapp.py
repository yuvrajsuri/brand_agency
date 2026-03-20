"""
WhatsApp Router
Handles incoming Meta Cloud API webhooks (GET verification + POST messages).
Routes messages to chatbot or campaign flow.
Replaces n8n workflows: 04_trigger_whatsapp_incoming, 06_svc_gemini_intent_classifier.
"""

import asyncio
import logging
from fastapi import APIRouter, Request, Query, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
import httpx

from config import settings
from services.pocketbase import PocketBaseClient
from services.whatsapp import WhatsAppSender
from services.chatbot import ChatbotService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["whatsapp"])

wa = WhatsAppSender()
pb = PocketBaseClient()
bot = ChatbotService()


@router.get("/whatsapp", response_class=PlainTextResponse)
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    """
    Meta webhook verification handshake.
    Meta sends GET with hub.mode=subscribe to verify our endpoint.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully")
        return hub_challenge
    logger.warning(f"Webhook verification failed — token mismatch")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/whatsapp")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    """
    Receive and process incoming WhatsApp messages.
    Immediately ACKs with 200 OK, then processes async to avoid Meta timeouts.
    """
    try:
        body = await request.json()
    except Exception:
        return {"status": "ok"}  # ACK even on bad payload

    # Always ACK immediately — Meta will retry if we're slow
    background_tasks.add_task(_process_webhook, body)
    return {"status": "ok"}


async def _process_webhook(body: dict):
    """Process the webhook payload asynchronously after ACK"""
    try:
        message = _parse_message(body)
        if not message:
            return  # Status update, not a user message

        logger.info(f"Message from {message['sender_phone']}: {message['message_text'][:80]}")

        # Mark as read
        await wa.mark_read(message["message_id"])

        # Look up client in PocketBase
        client = await pb.get_client_by_phone(message["sender_phone"])

        if client:
            # Known client — this is a B2B interaction (client with a subscription)
            await _handle_client_message(message, client)
        else:
            # Unknown number — B2C consumer chatbot
            await _handle_consumer_message(message)

    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)


async def _handle_consumer_message(message: dict):
    """B2C chatbot: respond to consumer inquiries directed at one of our clients"""

    # Classify intent
    intent_data = await _classify_intent(message["message_text"])
    intent = intent_data.get("intent", "unknown")
    language = intent_data.get("language", "english")

    logger.info(f"Consumer intent: {intent} ({language})")

    # Build response
    response_text = bot.get_quick_response(intent, language)
    buttons = bot.get_buttons_for_intent(intent, language)

    if buttons:
        await wa.send_quick_replies(message["sender_phone"], response_text, buttons)
    else:
        await wa.send_text(message["sender_phone"], response_text)

    # If it needs human escalation, alert the admin/owner
    if bot.should_escalate_to_human(intent) and settings.ADMIN_PHONE:
        alert = f"⚠️ Customer {message['sender_name']} ({message['sender_phone']}) needs attention.\nMessage: {message['message_text']}"
        await wa.send_text(settings.ADMIN_PHONE, alert)


async def _handle_client_message(message: dict, client: dict):
    """B2B client: handle requests from subscribed business owners"""

    text = message["message_text"].lower()

    # Campaign generation trigger keywords
    campaign_triggers = ["poster", "campaign", "ad", "generate", "ਪੋਸਟਰ", "ਕੈਂਪੇਨ", "पोस्टर"]

    if any(kw in text for kw in campaign_triggers):
        # Acknowledge and trigger campaign generation
        await wa.send_text(
            message["sender_phone"],
            f"✨ Campaign generate ho raha hai for {client.get('business_name', 'your business')}... thodi der baad poster milega!"
        )

        # Fire campaign request to Creative Engine
        await _trigger_campaign(client, message)
    else:
        # General greeting / unknown — respond with menu
        await wa.send_quick_replies(
            message["sender_phone"],
            f"*{client.get('business_name', 'Hello')}* ke liye kya chahiye?",
            [
                {"id": "btn_campaign", "title": "🎨 Generate Poster"},
                {"id": "btn_status", "title": "📊 Campaign Status"},
                {"id": "btn_help", "title": "❓ Help"}
            ]
        )


async def _trigger_campaign(client: dict, message: dict):
    """Trigger campaign generation via Creative Engine"""
    creative_url = settings.CREATIVE_ENGINE_URL

    payload = {
        "client_id": client.get("id"),
        "business_name": client.get("business_name", ""),
        "business_type": client.get("business_type", "retail"),
        "language": client.get("language", "punjabi"),
        "template_type": "offer",  # TODO: detect from message
        "brand_color": client.get("brand_color", "#FF6B35"),
        "count": 1
    }

    try:
        async with httpx.AsyncClient(timeout=180.0) as client_http:
            response = await client_http.post(
                f"{creative_url}/api/campaigns/generate",
                json=payload
            )
            if response.status_code == 200:
                data = response.json()
                posters = data.get("posters", [])

                for poster in posters:
                    # Send the generated poster
                    await wa.send_image(
                        message["sender_phone"],
                        poster["image_url"],
                        caption=f"*{poster['headline']}*\n{poster['subtext']}\n\n_{poster['cta']}_"
                    )
            else:
                await wa.send_text(
                    message["sender_phone"],
                    "⚠️ Campaign generate karne mein problem aayi. Please try again."
                )
    except Exception as e:
        logger.error(f"Campaign trigger failed: {e}")
        await wa.send_text(
            message["sender_phone"],
            "⚠️ Service temporarily unavailable. Please try again in a minute."
        )


async def _classify_intent(text: str) -> dict:
    """
    Classify message intent via the Creative Engine's Gemini service.
    Falls back to unknown if unavailable.
    """
    try:
        creative_url = settings.CREATIVE_ENGINE_URL
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{creative_url}/api/copy/classify-intent",
                json={"text": text}
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return {"intent": "unknown", "confidence": 0.0, "language": "english"}


def _parse_message(body: dict) -> dict | None:
    """
    Parse Meta webhook payload into a clean message dict.
    Returns None for status updates and other non-message events.
    """
    try:
        entry = body.get("entry", [{}])[0]
        change = entry.get("changes", [{}])[0]
        value = change.get("value", {})

        messages = value.get("messages", [])
        if not messages:
            return None  # Status update

        msg = messages[0]
        contact = value.get("contacts", [{}])[0]

        # Extract text based on message type
        message_type = msg.get("type", "unknown")
        if message_type == "text":
            text = msg.get("text", {}).get("body", "")
        elif message_type == "interactive":
            message_type = "button"
            text = (
                msg.get("interactive", {}).get("button_reply", {}).get("title") or
                msg.get("interactive", {}).get("list_reply", {}).get("title") or ""
            )
        elif message_type == "image":
            text = msg.get("image", {}).get("caption", "[Image]")
        elif message_type == "button":
            text = msg.get("button", {}).get("text", "")
        else:
            text = f"[{message_type}]"

        return {
            "sender_phone": msg.get("from"),
            "sender_name": contact.get("profile", {}).get("name", "Unknown"),
            "message_type": message_type,
            "message_text": text,
            "message_id": msg.get("id"),
            "timestamp": msg.get("timestamp"),
            "phone_number_id": value.get("metadata", {}).get("phone_number_id")
        }

    except Exception as e:
        logger.error(f"Message parse error: {e}")
        return None
