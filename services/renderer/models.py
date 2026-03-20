"""
Renderer Service — Pydantic Models
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field


class TextBlock(BaseModel):
    """Individual text element with styling"""
    content: str = Field(..., description="Text content in any language")
    type: Literal["headline", "subtext", "cta"] = Field(..., description="Type of text block")
    font_size: Optional[int] = Field(None, description="Font size in pixels (auto-calculated if None)")
    color: Optional[str] = Field("#FFFFFF", description="Text color in hex format")
    weight: Optional[Literal["normal", "bold", "black"]] = Field("bold", description="Font weight")


class OverlayRequest(BaseModel):
    """Request model for text overlay generation"""
    background_url: str = Field(..., description="URL or local path of the background image")
    texts: list[TextBlock] = Field(..., description="List of text blocks to overlay")
    language: Literal["punjabi", "hindi", "english"] = Field(..., description="Primary language")
    template_type: Literal["festival", "offer", "product", "event"] = Field(..., description="Template layout")
    brand_color: Optional[str] = Field("#FF6B35", description="Primary brand color for accents")
    output_width: Optional[int] = Field(1080, description="Output image width")
    output_height: Optional[int] = Field(1080, description="Output image height")


class OverlayResponse(BaseModel):
    """Response model with generated image details"""
    success: bool
    image_url: str
    generation_time: float
    metadata: dict
