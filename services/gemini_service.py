"""
Gemini API Service
Handles marketing copy generation and background image prompts
"""

import os
import logging
import json
import httpx
from typing import Dict

logger = logging.getLogger(__name__)


class GeminiService:
    """Google Gemini API integration for text and image generation"""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not configured - using fallback templates")
            self.api_key = None
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = "gemini-2.0-flash"  # Use Gemini 2.0 Flash
    
    async def generate_marketing_copy(
        self,
        business_name: str,
        business_type: str,
        language: str,
        template_type: str
    ) -> Dict[str, str]:
        """
        Generate headline, subtext, and CTA using Gemini
        """
        
        if not self.api_key:
            return self._get_fallback_copy(business_name, language, template_type)
        
        try:
            # Build prompt for Gemini
            prompt = self._build_copy_prompt(business_name, business_type, language, template_type)
            
            # Call Gemini API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{
                            "parts": [{
                                "text": prompt
                            }]
                        }],
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
                
                # Extract generated text
                generated_text = result['candidates'][0]['content']['parts'][0]['text']
                
                # Clean up markdown formatting (Gemini sometimes wraps JSON in ```json ```)
                generated_text = generated_text.strip()
                if generated_text.startswith('```json'):
                    generated_text = generated_text[7:]  # Remove ```json
                if generated_text.startswith('```'):
                    generated_text = generated_text[3:]  # Remove ```
                if generated_text.endswith('```'):
                    generated_text = generated_text[:-3]  # Remove ```
                generated_text = generated_text.strip()
                
                # Parse JSON response
                copy_data = json.loads(generated_text)
                
                logger.info(f"Gemini generated copy: {copy_data}")
                
                return copy_data
                
        except Exception as e:
            logger.error(f"Gemini copy generation failed: {str(e)}", exc_info=True)
            return self._get_fallback_copy(business_name, language, template_type)
    
    def _build_copy_prompt(self, business_name: str, business_type: str, language: str, template_type: str) -> str:
        """Build prompt for Gemini to generate marketing copy"""
        
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
        
        prompt = f"""You are a professional marketing copywriter specializing in {language_names[language]} content.

Create marketing copy for a {template_type} poster for "{business_name}", which is a {business_type} business.

The poster is for a {template_descriptions[template_type]}.

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

        return prompt
    
    async def generate_image_prompt(
        self,
        business_name: str,
        business_type: str,
        template_type: str,
        copy_text: str
    ) -> str:
        """
        Generate a prompt for background image generation
        """
        
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
                        "contents": [{
                            "parts": [{
                                "text": prompt
                            }]
                        }],
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
    
    async def get_background_image(self, prompt: str, template_type: str, business_type: str = "") -> str:
        """
        Get background image URL with contextually relevant images
        Uses Unsplash Source API with fallback to Picsum
        
        Note: Gemini Imagen 3 integration requires Vertex AI setup,
        which needs a Google Cloud project. For MVP, using Unsplash/Picsum.
        """
        
        import random
        seed = random.randint(1, 1000)
        
        # Map template types to relevant Unsplash keywords
        keywords_map = {
            "festival": "celebration,lights,decorations,festive",
            "offer": "sale,shopping,retail,discount",
            "product": "minimal,product,studio,clean",
            "event": "event,conference,gathering,professional"
        }
        
        # For food businesses, use food-related keywords
        business_lower = business_type.lower()
        if any(word in business_lower for word in ["food", "sweet", "restaurant", "cafe", "bakery", "kitchen"]):
            keywords = "food,sweets,dessert,cuisine,delicious"
        else:
            keywords = keywords_map.get(template_type, "abstract,gradient,minimal")
        
        # Try Unsplash first, with fallback to Picsum if it fails
        try:
            background_url = f"https://source.unsplash.com/1080x1080/?{keywords}&sig={seed}"
            
            # Test if Unsplash is accessible (quick HEAD request)
            async with httpx.AsyncClient(timeout=5.0) as client:
                try:
                    response = await client.head(background_url, follow_redirects=True)
                    if response.status_code == 200:
                        logger.info(f"Using Unsplash background (keywords={keywords}, seed={seed})")
                        return background_url
                    else:
                        raise Exception(f"Unsplash returned {response.status_code}")
                except Exception as e:
                    logger.warning(f"Unsplash check failed: {e}, using Picsum fallback")
                    raise  # Trigger fallback
                    
        except Exception:
            # Fallback to Picsum with blur for better text readability
            background_url = f"https://picsum.photos/1080/1080?random={seed}&blur=2"
            logger.info(f"Using Picsum fallback (seed={seed}): {background_url}")
            return background_url
    
    def _get_fallback_copy(self, business_name: str, language: str, template_type: str) -> Dict[str, str]:
        """Fallback templates when Gemini API is unavailable"""
        
        templates = {
            "punjabi": {
                "festival": {
                    "headline": "ਵਿਸ਼ੇਸ਼ ਤਿਉਹਾਰ ਦੀ ਪੇਸ਼ਕਸ਼",
                    "subtext": f"{business_name} ਤੋਂ ਵਿਸ਼ੇਸ਼ ਛੋਟਾਂ",
                    "cta": "ਹੁਣੇ ਆਰਡਰ ਕਰੋ"
                },
                "offer": {
                    "headline": "50% ਤੱਕ ਛੋਟ",
                    "subtext": f"{business_name} 'ਤੇ",
                    "cta": "ਖਰੀਦੋ ਹੁਣ"
                },
                "product": {
                    "headline": "ਨਵਾਂ ਉਤਪਾਦ",
                    "subtext": f"{business_name} ਤੋਂ",
                    "cta": "ਖਰੀਦੋ"
                },
                "event": {
                    "headline": "ਵਿਸ਼ੇਸ਼ ਸਮਾਗਮ",
                    "subtext": f"{business_name} ਵਿਖੇ",
                    "cta": "ਰਜਿਸਟਰ ਕਰੋ"
                }
            },
            "hindi": {
                "festival": {
                    "headline": "त्योहार की विशेष पेशकश",
                    "subtext": f"{business_name} से विशेष छूट",
                    "cta": "अभी ऑर्डर करें"
                },
                "offer": {
                    "headline": "50% तक की छूट",
                    "subtext": f"{business_name} पर",
                    "cta": "अभी खरीदें"
                },
                "product": {
                    "headline": "नया उत्पाद",
                    "subtext": f"{business_name} से",
                    "cta": "खरीदें"
                },
                "event": {
                    "headline": "विशेष कार्यक्रम",
                    "subtext": f"{business_name} में",
                    "cta": "पंजीकरण करें"
                }
            },
            "english": {
                "festival": {
                    "headline": "Festival Special Offer",
                    "subtext": f"Exclusive deals at {business_name}",
                    "cta": "Order Now"
                },
                "offer": {
                    "headline": "Up to 50% Off",
                    "subtext": f"At {business_name}",
                    "cta": "Shop Now"
                },
                "product": {
                    "headline": "New Product Launch",
                    "subtext": f"From {business_name}",
                    "cta": "Buy Now"
                },
                "event": {
                    "headline": "Special Event",
                    "subtext": f"At {business_name}",
                    "cta": "Register Now"
                }
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