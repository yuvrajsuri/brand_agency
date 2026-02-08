"""
Text Overlay Engine - FastAPI Application
Handles dynamic text overlay on images with Punjabi/Hindi support
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, Literal
import uvicorn
import logging
import sys
import asyncio
import os
from pathlib import Path
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background tasks
    asyncio.create_task(cleanup_cron())
    yield
    # Shutdown logic if needed

# Initialize FastAPI app
app = FastAPI(
    title="Text Overlay Engine",
    description="AI-powered text overlay for marketing images with Indic script support",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for n8n integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create static directory if it doesn't exist
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

async def cleanup_cron():
    """Background task to clean up old local files every hour"""
    while True:
        try:
            cleanup_old_local_files()
        except Exception as e:
            logger.error(f"Cleanup task failed: {str(e)}")
        await asyncio.sleep(3600)  # Run every hour

def cleanup_old_local_files():
    """Delete local overlay files older than 24 hours"""
    overlay_dir = STATIC_DIR / "overlays"
    if not overlay_dir.exists():
        return
        
    cutoff = time.time() - (24 * 3600)  # 24 hours ago
    count = 0
    
    for file_path in overlay_dir.glob("*"):
        if file_path.is_file():
            try:
                if file_path.stat().st_mtime < cutoff:
                    file_path.unlink()
                    count += 1
            except Exception as e:
                logger.error(f"Failed to delete {file_path}: {str(e)}")
    
    if count > 0:
        logger.info(f"Cleaned up {count} old local overlay files")


# Request/Response Models
class TextBlock(BaseModel):
    """Individual text element with styling"""
    content: str = Field(..., description="Text content in any language")
    type: Literal["headline", "subtext", "cta"] = Field(..., description="Type of text block")
    font_size: Optional[int] = Field(None, description="Font size in pixels (auto-calculated if None)")
    color: Optional[str] = Field("#FFFFFF", description="Text color in hex format")
    weight: Optional[Literal["normal", "bold", "black"]] = Field("bold", description="Font weight")


class OverlayRequest(BaseModel):
    """Request model for text overlay generation"""
    background_url: str = Field(..., description="URL of the background image (from Runware)")
    texts: list[TextBlock] = Field(..., description="List of text blocks to overlay")
    language: Literal["punjabi", "hindi", "english"] = Field(..., description="Primary language")
    template_type: Literal["festival", "offer", "product", "event"] = Field(..., description="Template type for dynamic positioning")
    brand_color: Optional[str] = Field("#FF6B35", description="Primary brand color for accents")
    output_width: Optional[int] = Field(1080, description="Output image width")
    output_height: Optional[int] = Field(1080, description="Output image height")


class OverlayResponse(BaseModel):
    """Response model with generated image details"""
    success: bool
    image_url: str
    generation_time: float
    metadata: dict


# Health check endpoint
@app.get("/")
async def root():
    """Serve the web interface"""
    # Check if index.html exists, otherwise return simpler message
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Text Overlay Engine Running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "text-overlay-engine",
        "version": "1.0.0"
    }


# Main overlay generation endpoint
@app.post("/api/upload-background")
async def upload_background(file: UploadFile = File(...)):
    """
    Upload background image and return temporary URL
    """
    import tempfile
    import shutil
    
    try:
        # Create temp directory
        temp_dir = Path(tempfile.gettempdir()) / "overlay-engine"
        temp_dir.mkdir(exist_ok=True)
        
        # Save uploaded file
        file_ext = Path(file.filename).suffix
        temp_file = temp_dir / f"upload_{os.urandom(8).hex()}{file_ext}"
        
        with temp_file.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Return file:// URL for local access
        file_path = str(temp_file.absolute())
        
        logger.info(f"Background uploaded: {temp_file}")
        
        return {
            "success": True,
            "url": str(file_path),
            "filename": file.filename
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/api/generate-overlay", response_model=OverlayResponse)
async def generate_overlay(request: OverlayRequest):
    """
    Generate text overlay on background image
    
    Process:
    1. Download background image from Runware
    2. Calculate dynamic text positions based on template type
    3. Render text using Playwright (proper Gurmukhi/Devanagari support)
    4. Upload to Cloudflare R2
    5. Return public URL
    """
    import time
    start_time = time.time()
    
    try:
        logger.info(f"Generating overlay: {request.template_type} template, {request.language} language")
        
        # Import services
        from services.renderer import OverlayRenderer
        from services.storage import R2Storage
        
        # Initialize services
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
        
        # Render overlay
        output_path = await renderer.render_overlay(
            background_path=background_path,
            text_blocks=request.texts,
            positions=positions,
            language=request.language,
            brand_color=request.brand_color,
            output_width=request.output_width,
            output_height=request.output_height
        )
        
        # Upload to R2 for production accessibility
        image_url = await storage.upload_image(output_path)
        
        generation_time = time.time() - start_time
        
        logger.info(f"Overlay generated successfully in {generation_time:.2f}s: {image_url}")
        
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
        logger.error(f"Error generating overlay: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Overlay generation failed: {str(e)}")


# Test endpoint for local development
@app.post("/api/test-overlay")
async def test_overlay():
    """
    Test endpoint with sample data for local testing
    """
    sample_request = OverlayRequest(
        background_url="https://example.com/sample-bg.jpg",
        texts=[
            TextBlock(content="ਵਿਸ਼ੇਸ਼ ਪੇਸ਼ਕਸ਼", type="headline", color="#FFFFFF", weight="black"),
            TextBlock(content="50% ਤੱਕ ਛੋਟ", type="subtext", color="#FFD700", weight="bold"),
            TextBlock(content="ਹੁਣੇ ਆਰਡਰ ਕਰੋ", type="cta", color="#FFFFFF", weight="bold")
        ],
        language="punjabi",
        template_type="offer",
        brand_color="#FF6B35"
    )
    
    return await generate_overlay(sample_request)


if __name__ == "__main__":
    # Windows fix: Set event loop policy before uvicorn starts
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload on Windows (conflicts with event loop policy)
        log_level="info"
    )
