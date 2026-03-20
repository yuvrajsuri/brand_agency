"""
Images Router — standalone image generation endpoint
"""

import logging
from fastapi import APIRouter, HTTPException
from models import ImageRequest, ImageResponse
from services.image_gen import ImageGenService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/images", tags=["images"])
image_gen = ImageGenService()


@router.post("/generate", response_model=ImageResponse)
async def generate_image(request: ImageRequest):
    """Generate a background image using Imagen / Runware / Unsplash fallback"""
    try:
        url, source = await image_gen.generate_background(
            prompt=request.prompt,
            template_type=request.template_type,
            business_type=request.business_type,
            width=request.width,
            height=request.height
        )
        return ImageResponse(image_url=url, source=source)
    except Exception as e:
        logger.error(f"Image generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
