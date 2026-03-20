"""
Audit Router — standalone quality audit endpoint
"""

import logging
from fastapi import APIRouter, HTTPException
from models import AuditRequest, AuditResponse
from services.quality import QualityAuditService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/audit", tags=["audit"])
auditor = QualityAuditService()


@router.post("", response_model=AuditResponse)
async def audit_creative(request: AuditRequest):
    """Run Gemini Vision quality audit on a generated creative"""
    try:
        result = await auditor.audit(
            image_url=request.image_url,
            expected_text=request.expected_text,
            style_constraints=request.style_constraints or "Professional, culturally appropriate for Punjab"
        )
        return AuditResponse(**result)
    except Exception as e:
        logger.error(f"Audit failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
