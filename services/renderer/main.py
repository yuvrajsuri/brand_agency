"""
Renderer Service — FastAPI Application
Handles text overlay on images with Punjabi/Hindi/English support using Playwright.
This is a standalone microservice that can be scaled independently.
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import sys
import asyncio
import time

from models import OverlayRequest, OverlayResponse

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI(
    title="Renderer Service",
    description="Text overlay engine with Indic script support (Gurmukhi, Devanagari)",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "renderer",
        "version": "2.0.0"
    }


@app.post("/api/render", response_model=OverlayResponse)
async def render_overlay(request: OverlayRequest):
    """
    Generate text overlay on a background image.

    Process:
    1. Download background image
    2. Calculate dynamic text positions based on template type
    3. Render text using Playwright (proper Gurmukhi/Devanagari support)
    4. Upload to Cloudflare R2 (or local storage)
    5. Return public URL

    This endpoint is called by the Creative Engine service.
    """
    start_time = time.time()

    try:
        logger.info(f"Rendering overlay: {request.template_type} template, {request.language} language")

        from services.renderer import OverlayRenderer
        from services.storage import R2Storage

        renderer = OverlayRenderer()
        storage = R2Storage()

        # Download background image
        background_path = await renderer.download_background(request.background_url)

        # Calculate dynamic positions based on template type
        positions = renderer.calculate_positions(
            template_type=request.template_type,
            text_blocks=request.texts,
            image_width=request.output_width,
            image_height=request.output_height
        )

        # Render overlay with flexbox layout
        output_path = await renderer.render_overlay(
            background_path=background_path,
            text_blocks=request.texts,
            positions=positions,
            language=request.language,
            brand_color=request.brand_color,
            output_width=request.output_width,
            output_height=request.output_height,
            template_type=request.template_type
        )

        # Upload to R2
        image_url = await storage.upload_image(output_path)

        generation_time = time.time() - start_time

        logger.info(f"Overlay rendered in {generation_time:.2f}s: {image_url}")

        return OverlayResponse(
            success=True,
            image_url=image_url,
            generation_time=generation_time,
            metadata={
                "template_type": request.template_type,
                "language": request.language,
                "text_blocks": len(request.texts),
                "dimensions": f"{request.output_width}x{request.output_height}"
            }
        )

    except Exception as e:
        logger.error(f"Render failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Render failed: {str(e)}")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
        log_level="info"
    )
