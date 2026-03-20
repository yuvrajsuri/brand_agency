"""
Chatbot Service
Handles B2C consumer chatbot responses on WhatsApp.
Simple rule-based + Gemini-backed replies for common inquiries.
"""

import logging
import json
import httpx
from config import settings

logger = logging.getLogger(__name__)

# Quick reply templates per intent + language
RESPONSES = {
    "greeting": {
        "punjabi": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! 🙏 ਮੈਂ ਤੁਹਾਡੀ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?",
        "hindi": "नमस्ते! 🙏 मैं आपकी कैसे मदद कर सकता हूँ?",
        "english": "Hello! 👋 How can I help you today?"
    },
    "product_inquiry": {
        "punjabi": "ਸਾਡੇ ਉਤਪਾਦਾਂ ਬਾਰੇ ਜਾਣਕਾਰੀ ਲਈ ਕਿਰਪਾ ਕਰਕੇ ਇੱਕ ਮਿੰਟ ਉਡੀਕ ਕਰੋ।",
        "hindi": "हमारे उत्पादों की जानकारी के लिए एक मिनट प्रतीक्षा करें।",
        "english": "I'll get you product details in just a moment!"
    },
    "pricing": {
        "punjabi": "ਸਾਡੀਆਂ ਕੀਮਤਾਂ ਬਾਰੇ ਜਾਣਨ ਲਈ ਦੁਕਾਨਦਾਰ ਨਾਲ ਸੰਪਰਕ ਕਰੋ।",
        "hindi": "कीमतों के लिए दुकानदार से संपर्क करें।",
        "english": "Let me connect you with the shop owner for pricing."
    },
    "human_request": {
        "punjabi": "ਤੁਹਾਡੀ ਬੇਨਤੀ ਦੁਕਾਨਦਾਰ ਤੱਕ ਪਹੁੰਚਾਈ ਜਾ ਰਹੀ ਹੈ। ਜਲਦੀ ਜਵਾਬ ਆਵੇਗਾ।",
        "hindi": "आपकी बात दुकानदार तक पहुँचाई जा रही है।",
        "english": "Connecting you to the shop owner — they'll reply shortly!"
    },
    "unknown": {
        "punjabi": "ਮਾਫ਼ ਕਰਨਾ, ਮੈਂ ਸਮਝ ਨਹੀਂ ਸਕਿਆ। ਕਿਰਪਾ ਕਰਕੇ ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ।",
        "hindi": "माफ़ करें, मैं समझ नहीं पाया। कृपया फिर से कोशिश करें।",
        "english": "Sorry, I didn't quite understand. Could you rephrase that?"
    }
}


class ChatbotService:
    """Handles B2C chatbot responses"""

    def get_quick_response(self, intent: str, language: str) -> str:
        """Return a canned response for an intent"""
        lang = language if language in ("punjabi", "hindi", "english") else "english"
        intent_key = intent if intent in RESPONSES else "unknown"
        return RESPONSES[intent_key][lang]

    def should_escalate_to_human(self, intent: str) -> bool:
        """Determine if we need to alert the business owner"""
        return intent in ("human_request", "order_reserve", "store_location")

    def get_buttons_for_intent(self, intent: str, language: str) -> list[dict]:
        """Return contextual quick reply buttons"""
        if intent == "greeting":
            return [
                {"id": "btn_offers", "title": "🎁 Current Offers"},
                {"id": "btn_products", "title": "🛍️ Products"},
                {"id": "btn_contact", "title": "📞 Contact Owner"}
            ]
        elif intent in ("product_inquiry", "pricing"):
            return [
                {"id": "btn_more_info", "title": "More Info"},
                {"id": "btn_contact", "title": "📞 Call Owner"}
            ]
        return []
