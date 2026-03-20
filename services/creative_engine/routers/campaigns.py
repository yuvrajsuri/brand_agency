"""
Campaigns Router — Campaign Generation Pipeline
Orchestrates the full generate → render → audit → retry loop.
This is the core business logic that was previously fragmented across n8n workflows.
"""

import asyncio
import logging
import time
from typing import List

import httpx
from fastapi import APIRouter, HTTPException, BackgroundTasks

from models import CampaignRequest, CampaignResponse, GeneratedPoster
from services.gemini import GeminiService
from services.image_gen import ImageGenService
from services.quality import QualityAuditService
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

gemini = GeminiService()
image_gen = ImageGenService()
auditor = QualityAuditService()


@router.post("/generate", response_model=CampaignResponse)
async def generate_campaign(request: CampaignRequest):
    """
    Full campaign generation pipeline.

    For each poster requested:
    1. Generate marketing copy (Gemini)
    2. Generate image prompt (Gemini)
    3. Generate background image (Imagen → Runware → Unsplash)
    4. Send to Renderer service for text overlay
    5. Quality audit (Gemini Vision)
    6. If audit fails, retry up to MAX_RETRIES times
    7. Return all generated posters
    """
    start_time = time.time()
    posters: List[GeneratedPoster] = []

    for i in range(request.count):
        logger.info(f"Generating poster {i + 1}/{request.count} for {request.business_name}")

        poster = await _generate_single_poster(
            business_name=request.business_name,
            business_type=request.business_type,
            language=request.language,
            template_type=request.template_type,
            occasion=request.occasion,
            brand_color=request.brand_color or "#FF6B35",
        )

        if poster:
            posters.append(poster)

    total_time = time.time() - start_time
    logger.info(f"Campaign done: {len(posters)}/{request.count} posters in {total_time:.2f}s")

    return CampaignResponse(
        success=len(posters) > 0,
        posters=posters,
        generation_time=total_time
    )


async def _generate_single_poster(
    business_name: str,
    business_type: str,
    language: str,
    template_type: str,
    occasion: str,
    brand_color: str,
) -> GeneratedPoster | None:
    """Generate a single poster with retries on quality failure"""

    MAX_RETRIES = settings.AUDIT_MAX_RETRIES

    # Step 1: Generate marketing copy
    copy = await gemini.generate_marketing_copy(
        business_name=business_name,
        business_type=business_type,
        language=language,
        template_type=template_type,
        occasion=occasion
    )

    headline = copy.get("headline", "")
    subtext = copy.get("subtext", "")
    cta = copy.get("cta", "")

    # Step 2: Generate image prompt
    copy_summary = f"{headline} — {subtext}"
    image_prompt = await gemini.generate_image_prompt(
        business_name=business_name,
        business_type=business_type,
        template_type=template_type,
        copy_text=copy_summary
    )

    # Step 3–6: Generate image → render → audit → retry loop
    for attempt in range(1, MAX_RETRIES + 1):
        logger.info(f"Attempt {attempt}/{MAX_RETRIES}: generating background + rendering")

        # Generate background image
        bg_url, bg_source = await image_gen.generate_background(
            prompt=image_prompt,
            template_type=template_type,
            business_type=business_type
        )

        # Send to Renderer service
        rendered_url = await _call_renderer(
            background_url=bg_url,
            headline=headline,
            subtext=subtext,
            cta=cta,
            language=language,
            template_type=template_type,
            brand_color=brand_color
        )

        if not rendered_url:
            logger.warning(f"Attempt {attempt}: renderer returned nothing")
            continue

        # Quality audit
        audit = await auditor.audit(
            image_url=rendered_url,
            expected_text=f"{headline} {subtext} {cta}",
            style_constraints=f"Professional, culturally appropriate for Punjab, {template_type} poster"
        )

        if audit["passed"] or attempt == MAX_RETRIES:
            if not audit["passed"]:
                logger.warning(f"Poster failed audit after {MAX_RETRIES} attempts — using anyway")
            return GeneratedPoster(
                image_url=rendered_url,
                headline=headline,
                subtext=subtext,
                cta=cta,
                audit_score=audit["score"],
                audit_passed=audit["passed"]
            )

        logger.info(f"Audit failed (score={audit['score']:.2f}), retrying... Issues: {audit['issues']}")

    return None


async def _call_renderer(
    background_url: str,
    headline: str,
    subtext: str,
    cta: str,
    language: str,
    template_type: str,
    brand_color: str
) -> str | None:
    """
    Call the Renderer microservice to apply text overlay.
    POSTs to http://renderer:8002/api/render
    """
    renderer_url = settings.RENDERER_URL

    payload = {
        "background_url": background_url,
        "texts": [
            {"content": headline, "type": "headline", "color": "#FFFFFF", "weight": "black"},
            {"content": subtext, "type": "subtext", "color": "#FFD700", "weight": "bold"},
            {"content": cta, "type": "cta", "color": "#FFFFFF", "weight": "bold"}
        ],
        "language": language,
        "template_type": template_type,
        "brand_color": brand_color,
        "output_width": 1080,
        "output_height": 1080
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{renderer_url}/api/render", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("image_url")

    except httpx.TimeoutException:
        logger.error("Renderer service timed out")
        return None
    except Exception as e:
        logger.error(f"Renderer call failed: {e}")
        return None
