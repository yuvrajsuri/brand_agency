"""
Image Generation Service
Handles background image generation via Google Imagen and Runware (Flux Schnell).
Falls back to Unsplash / Picsum if both fail.
"""

import base64
import logging
import os
import tempfile
import httpx
import json
from pathlib import Path
from typing import Tuple

from config import settings

logger = logging.getLogger(__name__)


class ImageGenService:
    """Generates background images for marketing posters"""

    def __init__(self):
        self.gemini_key = settings.GEMINI_API_KEY
        self.runware_key = settings.RUNWARE_API_KEY
        self.gemini_base = settings.GEMINI_BASE_URL
        self.imagen_model = settings.IMAGEN_MODEL

    async def generate_background(
        self,
        prompt: str,
        template_type: str,
        business_type: str = "",
        width: int = 1080,
        height: int = 1080
    ) -> Tuple[str, str]:
        """
        Generate a background image, trying sources in order:
        1. Google Imagen 4 (best quality)
        2. Runware / Flux Schnell (fast, good quality)
        3. Unsplash (free, stock)
        4. Picsum (final fallback)

        Returns: (image_url_or_path, source_label)
        """

        # 1. Try Google Imagen
        if self.gemini_key:
            result = await self._try_imagen(prompt, width, height)
            if result:
                return result, "imagen"

        # 2. Try Runware
        if self.runware_key:
            result = await self._try_runware(prompt, width, height)
            if result:
                return result, "runware"

        # 3. Unsplash / Picsum fallback
        url = await self._get_fallback(template_type, business_type)
        return url, "unsplash"

    async def _try_imagen(self, prompt: str, width: int, height: int) -> str | None:
        """Try Google Imagen 4 for background generation"""
        try:
            aspect = "1:1" if width == height else ("9:16" if height > width else "16:9")

            logger.info(f"Trying Imagen 4: {prompt[:60]}...")
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.gemini_base}/models/{self.imagen_model}:predict?key={self.gemini_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "instances": [{"prompt": prompt}],
                        "parameters": {"sampleCount": 1, "aspectRatio": aspect}
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    b64_image = result['predictions'][0]['bytesBase64Encoded']
                    image_data = base64.b64decode(b64_image)

                    tmp = Path(tempfile.gettempdir()) / f"imagen_{os.urandom(8).hex()}.png"
                    tmp.write_bytes(image_data)

                    logger.info(f"Imagen 4 success: {tmp}")
                    return str(tmp)
                else:
                    logger.warning(f"Imagen 4 failed: {response.status_code} — {response.text[:200]}")
                    return None

        except Exception as e:
            logger.warning(f"Imagen 4 error: {e}")
            return None

    async def _try_runware(self, prompt: str, width: int, height: int) -> str | None:
        """Try Runware (Flux Schnell) for background generation"""
        try:
            logger.info(f"Trying Runware: {prompt[:60]}...")
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.runware.ai/v1",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.runware_key}"
                    },
                    json=[{
                        "taskType": "imageInference",
                        "taskUUID": os.urandom(16).hex(),
                        "positivePrompt": prompt,
                        "width": width,
                        "height": height,
                        "model": "runware:100@1",  # Flux Schnell
                        "numberResults": 1,
                        "outputType": "URL",
                        "outputFormat": "PNG"
                    }]
                )

                if response.status_code == 200:
                    result = response.json()
                    # Runware returns array of task results
                    for item in result.get("data", []):
                        if item.get("taskType") == "imageInference":
                            url = item.get("imageURL")
                            if url:
                                logger.info(f"Runware success: {url}")
                                return url
                    logger.warning("Runware returned no image URL")
                    return None
                else:
                    logger.warning(f"Runware failed: {response.status_code} — {response.text[:200]}")
                    return None

        except Exception as e:
            logger.warning(f"Runware error: {e}")
            return None

    async def _get_fallback(self, template_type: str, business_type: str) -> str:
        """Fallback to Unsplash or Picsum"""
        import random
        seed = random.randint(1, 1000)

        keywords_map = {
            "festival": "celebration,lights,decorations,festive",
            "offer": "sale,shopping,retail,discount",
            "product": "minimal,product,studio,clean",
            "event": "event,conference,gathering,professional"
        }

        business_lower = business_type.lower()
        if any(word in business_lower for word in ["food", "sweet", "restaurant", "cafe", "bakery", "kitchen"]):
            keywords = "food,sweets,dessert,cuisine,delicious"
        else:
            keywords = keywords_map.get(template_type, "abstract,gradient,minimal")

        url = f"https://source.unsplash.com/1080x1080/?{keywords}&sig={seed}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.head(url, follow_redirects=True)
                if resp.status_code == 200:
                    return url
        except Exception:
            pass

        logger.info(f"Using Picsum fallback (seed={seed})")
        return f"https://picsum.photos/1080/1080?random={seed}&blur=2"
