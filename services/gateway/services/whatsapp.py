"""
WhatsApp Service
Handles sending messages and media via Meta Cloud API.
Replaces n8n workflow 02_util_whatsapp_send.
"""

import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

META_API_BASE = "https://graph.facebook.com/v19.0"


class WhatsAppSender:
    """Meta Cloud API client for sending WhatsApp messages"""

    def __init__(self):
        self.token = settings.META_ACCESS_TOKEN
        self.phone_id = settings.META_PHONE_NUMBER_ID

    async def send_text(self, to: str, body: str) -> bool:
        """Send a plain text message"""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": body}
        }
        return await self._send(payload)

    async def send_image(self, to: str, image_url: str, caption: str = "") -> bool:
        """Send an image message with optional caption"""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "image",
            "image": {"link": image_url, "caption": caption}
        }
        return await self._send(payload)

    async def send_quick_replies(self, to: str, body: str, buttons: list[dict]) -> bool:
        """
        Send an interactive message with quick-reply buttons.
        buttons = [{"id": "btn_id", "title": "Button Text"}, ...]
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                        for b in buttons[:3]  # Meta allows max 3 buttons
                    ]
                }
            }
        }
        return await self._send(payload)

    async def send_list(self, to: str, header: str, body: str, sections: list[dict]) -> bool:
        """Send an interactive list message"""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": header},
                "body": {"text": body},
                "action": {
                    "button": "View Options",
                    "sections": sections
                }
            }
        }
        return await self._send(payload)

    async def mark_read(self, message_id: str) -> bool:
        """Mark a message as read"""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        return await self._send(payload)

    async def _send(self, payload: dict) -> bool:
        """Internal helper to POST to Meta Graph API"""
        if not self.token:
            logger.warning("META_ACCESS_TOKEN not configured — skipping send")
            return False
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{META_API_BASE}/{self.phone_id}/messages",
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                if response.status_code == 200:
                    return True
                logger.error(f"WhatsApp send failed: {response.status_code} — {response.text[:300]}")
                return False
        except Exception as e:
            logger.error(f"WhatsApp send error: {e}")
            return False
