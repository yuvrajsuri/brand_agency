"""
Text Overlay Engine - FastAPI Application
Handles dynamic text overlay on images with Punjabi/Hindi support
"""

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

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

# Initialize FastAPI app
app = FastAPI(
    title="Text Overlay Engine",
    description="AI-powered text overlay for marketing images with Indic script support",
    version="1.0.0"
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
    """Serve the login page"""
    return FileResponse(str(STATIC_DIR / "login.html"))


@app.get("/chat.html")
async def chat_page():
    """Serve the chat interface"""
    return FileResponse(str(STATIC_DIR / "chat.html"))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "text-overlay-engine",
        "version": "1.0.0"
    }


class PosterRequest(BaseModel):
    """Request model for chatbot poster generation"""
    business_name: str
    business_type: str
    language: Literal["punjabi", "hindi", "english"]
    template_type: Literal["festival", "offer", "product", "event"]
    count: int = 1  # Number of variations


class GeneratedPoster(BaseModel):
    """Generated poster data"""
    image_url: str
    headline: str
    subtext: str
    cta: str


class PosterResponse(BaseModel):
    """Response with generated posters"""
    success: bool
    posters: list[GeneratedPoster]
    generation_time: float


@app.post("/api/generate-poster", response_model=PosterResponse)
async def generate_poster(request: PosterRequest):
    """
    Generate poster using Gemini API for copy + background generation
    Then overlay text with Playwright
    """
    import time
    start_time = time.time()
    
    try:
        logger.info(f"Generating poster for: {request.business_name}, template: {request.template_type}, count: {request.count}")
        
        # Import Gemini service
        from services.gemini_service import GeminiService
        from services.renderer import OverlayRenderer
        from services.storage import R2Storage
        
        gemini = GeminiService()
        renderer = OverlayRenderer()
        storage = R2Storage()
        
        posters = []
        
        for i in range(request.count):
            logger.info(f"Generating variation {i+1}/{request.count}")
            
            # Step 1: Generate marketing copy with Gemini
            copy_data = await gemini.generate_marketing_copy(
                business_name=request.business_name,
                business_type=request.business_type,
                language=request.language,
                template_type=request.template_type
            )
            
            # Step 2: Generate background image with Gemini
            background_prompt = await gemini.generate_image_prompt(
                business_name=request.business_name,
                business_type=request.business_type,
                template_type=request.template_type,
                copy_text=copy_data['headline']
            )
            
            # For now, use Unsplash as fallback (Gemini Imagen integration coming)
            background_url = await gemini.get_background_image(background_prompt, request.template_type)
            
            # Step 3: Download background
            background_path = await renderer.download_background(background_url)
            
            # Step 4: Calculate positions
            text_blocks = [
                type('obj', (object,), {'content': copy_data['headline'], 'type': 'headline', 'color': '#FFFFFF', 'weight': 'black', 'font_size': None})(),
                type('obj', (object,), {'content': copy_data['subtext'], 'type': 'subtext', 'color': '#FFD700', 'weight': 'bold', 'font_size': None})(),
                type('obj', (object,), {'content': copy_data['cta'], 'type': 'cta', 'color': '#FFFFFF', 'weight': 'bold', 'font_size': None})()
            ]
            
            positions = renderer.calculate_positions(
                template_type=request.template_type,
                text_blocks=text_blocks,
                image_width=1080,
                image_height=1080
            )
            
            # Step 5: Render overlay
            output_path = await renderer.render_overlay(
                background_path=background_path,
                text_blocks=text_blocks,
                positions=positions,
                language=request.language,
                brand_color="#FF6B35",
                output_width=1080,
                output_height=1080
            )
            
            # Step 6: Upload to R2 (or local)
            image_url = await storage.upload_image(output_path, folder="chatbot-posters")
            
            posters.append(GeneratedPoster(
                image_url=image_url,
                headline=copy_data['headline'],
                subtext=copy_data['subtext'],
                cta=copy_data['cta']
            ))
            
            logger.info(f"Variation {i+1} generated: {image_url}")
        
        generation_time = time.time() - start_time
        
        logger.info(f"All posters generated in {generation_time:.2f}s")
        
        return PosterResponse(
            success=True,
            posters=posters,
            generation_time=generation_time
        )
        
    except Exception as e:
        logger.error(f"Poster generation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Poster generation failed: {str(e)}")


@app.post("/api/upload-background")
async def upload_background(file: UploadFile = File(...)):
    """
    Upload background image and return temporary path
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
        
        # Return the absolute path as string (works with both Windows and Linux)
        file_path = str(temp_file.absolute())
        
        logger.info(f"Background uploaded: {file_path}")
        
        return {
            "success": True,
            "url": file_path,  # Direct path instead of file:// URL
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
        
        # Upload to R2
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
