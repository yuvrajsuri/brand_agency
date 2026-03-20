"""
Copy Router — standalone copy generation endpoint
"""

import logging
from fastapi import APIRouter, HTTPException
from models import CopyRequest, CopyResponse
from services.gemini import GeminiService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/copy", tags=["copy"])
gemini = GeminiService()


@router.post("/generate", response_model=CopyResponse)
async def generate_copy(request: CopyRequest):
    """Generate marketing copy (headline, subtext, CTA) using Gemini"""
    try:
        result = await gemini.generate_marketing_copy(
            business_name=request.business_name,
            business_type=request.business_type,
            language=request.language,
            template_type=request.template_type,
            occasion=request.occasion
        )
        return CopyResponse(**result)
    except Exception as e:
        logger.error(f"Copy generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
