"""
Gemini API Service — Copy Generation & Prompt Engineering
Handles marketing copy generation in Punjabi/Hindi/English.
"""

import json
import logging
import httpx
from typing import Dict

from config import settings

logger = logging.getLogger(__name__)


class GeminiService:
    """Gemini API client for text generation"""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.base_url = settings.GEMINI_BASE_URL
        self.model = settings.GEMINI_MODEL

        if not self.api_key:
            logger.warning("GEMINI_API_KEY not configured — using fallback templates")

    async def generate_marketing_copy(
        self,
        business_name: str,
        business_type: str,
        language: str,
        template_type: str,
        occasion: str = None
    ) -> Dict[str, str]:
        """Generate headline, subtext, and CTA using Gemini"""

        if not self.api_key:
            return self._get_fallback_copy(business_name, language, template_type)

        try:
            prompt = self._build_copy_prompt(business_name, business_type, language, template_type, occasion)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.9,
                            "maxOutputTokens": 200
                        }
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                    return self._get_fallback_copy(business_name, language, template_type)

                result = response.json()
                generated_text = result['candidates'][0]['content']['parts'][0]['text']

                # Clean markdown wrapping
                generated_text = generated_text.strip()
                if generated_text.startswith('```json'):
                    generated_text = generated_text[7:]
                if generated_text.startswith('```'):
                    generated_text = generated_text[3:]
                if generated_text.endswith('```'):
                    generated_text = generated_text[:-3]
                generated_text = generated_text.strip()

                copy_data = json.loads(generated_text)
                logger.info(f"Gemini generated copy: {copy_data}")
                return copy_data

        except Exception as e:
            logger.error(f"Gemini copy generation failed: {str(e)}", exc_info=True)
            return self._get_fallback_copy(business_name, language, template_type)

    async def generate_image_prompt(
        self,
        business_name: str,
        business_type: str,
        template_type: str,
        copy_text: str
    ) -> str:
        """Generate a prompt for background image generation"""

        if not self.api_key:
            return self._get_fallback_image_prompt(template_type)

        try:
            prompt = f"""Create a prompt for generating a background image for a marketing poster.

Business: {business_name} ({business_type})
Template Type: {template_type}
Main Message: {copy_text}

Generate a concise prompt (30-50 words) for an AI image generator that will create a suitable background.

Requirements:
- NO TEXT in the image (text-free background only)
- Visually appealing and professional
- Appropriate for {template_type} theme
- High contrast for readable text overlay
- Cultural sensitivity

Return ONLY the image prompt (plain text, no JSON):"""

            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.7,
                            "maxOutputTokens": 100
                        }
                    }
                )

                if response.status_code != 200:
                    return self._get_fallback_image_prompt(template_type)

                result = response.json()
                image_prompt = result['candidates'][0]['content']['parts'][0]['text'].strip()
                logger.info(f"Generated image prompt: {image_prompt}")
                return image_prompt

        except Exception as e:
            logger.error(f"Image prompt generation failed: {str(e)}")
            return self._get_fallback_image_prompt(template_type)

    async def classify_intent(self, message: str, language: str = "auto") -> Dict:
        """Classify user intent from a WhatsApp message.
        Used by the Gateway service via HTTP.
        """

        if not self.api_key:
            return {"intent": "unknown", "confidence": 0.0, "language": "english"}

        try:
            prompt = f"""Classify the intent of this WhatsApp message from a customer.

Message: "{message}"

Categories:
- product_inquiry: asking about products, availability, stock
- pricing: asking about prices, costs, discounts
- offer_details: asking about current offers, sales, deals
- store_location: asking about location, address, timings
- order_reserve: wanting to order, book, or reserve something
- human_request: wants to talk to owner, call me, complaint
- greeting: hello, hi, sat sri akal, namaste
- campaign_request: wants marketing help, create campaign, generate poster
- unknown: cannot classify

Also detect the language (punjabi, hindi, english).

Return ONLY JSON (no markdown):
{{"intent": "category", "confidence": 0.0-1.0, "language": "detected_language", "entities": {{}}}}"""

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.2,
                            "maxOutputTokens": 200,
                            "responseMimeType": "application/json"
                        }
                    }
                )

                if response.status_code != 200:
                    return {"intent": "unknown", "confidence": 0.0, "language": "english"}

                result = response.json()
                raw_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                return json.loads(raw_text)

        except Exception as e:
            logger.error(f"Intent classification failed: {str(e)}")
            return {"intent": "unknown", "confidence": 0.0, "language": "english"}

    def _build_copy_prompt(self, business_name, business_type, language, template_type, occasion=None):
        """Build prompt for marketing copy generation"""

        language_names = {
            "punjabi": "Punjabi (Gurmukhi script)",
            "hindi": "Hindi (Devanagari script)",
            "english": "English"
        }

        template_descriptions = {
            "festival": "festive celebration (like Diwali, Holi, Eid, Christmas)",
            "offer": "special sale or discount offer",
            "product": "new product launch or showcase",
            "event": "special event or workshop"
        }

        occasion_context = f"\nOccasion: {occasion}" if occasion else ""

        return f"""You are a professional marketing copywriter specializing in {language_names[language]} content.

Create marketing copy for a {template_type} poster for "{business_name}", which is a {business_type} business.

The poster is for a {template_descriptions[template_type]}.{occasion_context}

Generate THREE text elements in {language_names[language]}:
1. HEADLINE: A catchy, attention-grabbing headline (3-6 words, bold and impactful)
2. SUBTEXT: Supporting information or offer details (5-10 words, describes the value)
3. CTA: Call-to-action button text (2-4 words, action-oriented)

IMPORTANT RULES:
- Write ONLY in {language_names[language]} language (NOT English unless language is English)
- Keep text SHORT and PUNCHY
- Make it culturally appropriate for the festival/occasion
- Headline should be the MOST eye-catching
- CTA should be action-oriented (Shop Now, Order Now, Register, etc.)

Return ONLY a JSON object in this exact format (no markdown, no backticks):
{{"headline": "your headline here", "subtext": "your subtext here", "cta": "your cta here"}}"""

    def _get_fallback_copy(self, business_name: str, language: str, template_type: str) -> Dict[str, str]:
        """Fallback templates when Gemini API is unavailable"""

        templates = {
            "punjabi": {
                "festival": {"headline": "ਵਿਸ਼ੇਸ਼ ਤਿਉਹਾਰ ਦੀ ਪੇਸ਼ਕਸ਼", "subtext": f"{business_name} ਤੋਂ ਵਿਸ਼ੇਸ਼ ਛੋਟਾਂ", "cta": "ਹੁਣੇ ਆਰਡਰ ਕਰੋ"},
                "offer": {"headline": "50% ਤੱਕ ਛੋਟ", "subtext": f"{business_name} 'ਤੇ", "cta": "ਖਰੀਦੋ ਹੁਣ"},
                "product": {"headline": "ਨਵਾਂ ਉਤਪਾਦ", "subtext": f"{business_name} ਤੋਂ", "cta": "ਖਰੀਦੋ"},
                "event": {"headline": "ਵਿਸ਼ੇਸ਼ ਸਮਾਗਮ", "subtext": f"{business_name} ਵਿਖੇ", "cta": "ਰਜਿਸਟਰ ਕਰੋ"},
            },
            "hindi": {
                "festival": {"headline": "त्योहार की विशेष पेशकश", "subtext": f"{business_name} से विशेष छूट", "cta": "अभी ऑर्डर करें"},
                "offer": {"headline": "50% तक की छूट", "subtext": f"{business_name} पर", "cta": "अभी खरीदें"},
                "product": {"headline": "नया उत्पाद", "subtext": f"{business_name} से", "cta": "खरीदें"},
                "event": {"headline": "विशेष कार्यक्रम", "subtext": f"{business_name} में", "cta": "पंजीकरण करें"},
            },
            "english": {
                "festival": {"headline": "Festival Special Offer", "subtext": f"Exclusive deals at {business_name}", "cta": "Order Now"},
                "offer": {"headline": "Up to 50% Off", "subtext": f"At {business_name}", "cta": "Shop Now"},
                "product": {"headline": "New Product Launch", "subtext": f"From {business_name}", "cta": "Buy Now"},
                "event": {"headline": "Special Event", "subtext": f"At {business_name}", "cta": "Register Now"},
            }
        }

        logger.info("Using fallback copy template")
        return templates[language][template_type]

    def _get_fallback_image_prompt(self, template_type: str) -> str:
        """Fallback image prompts"""
        prompts = {
            "festival": "Colorful festive celebration background with lights and decorations, no text, vibrant and joyful",
            "offer": "Modern gradient background with sale theme, clean and professional, no text",
            "product": "Clean minimal product photography background, soft lighting, professional, no text",
            "event": "Modern event conference background, professional and elegant, no text"
        }
        return prompts.get(template_type, "Abstract gradient background, professional, no text")
