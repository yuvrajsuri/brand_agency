"""
Creative Engine Service — Pydantic Models
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field


# --- Copy Generation ---

class CopyRequest(BaseModel):
    """Request to generate marketing copy"""
    business_name: str
    business_type: str
    language: Literal["punjabi", "hindi", "english"]
    template_type: Literal["festival", "offer", "product", "event"]
    occasion: Optional[str] = None


class CopyResponse(BaseModel):
    """Generated marketing copy"""
    headline: str
    subtext: str
    cta: str


# --- Image Generation ---

class ImageRequest(BaseModel):
    """Request to generate a background image"""
    prompt: str = Field(..., description="Image generation prompt")
    template_type: Literal["festival", "offer", "product", "event"]
    business_type: str = ""
    width: int = 1080
    height: int = 1080


class ImageResponse(BaseModel):
    """Generated image details"""
    image_url: str
    source: str  # "imagen", "runware", "unsplash", "picsum"


# --- Quality Audit ---

class AuditRequest(BaseModel):
    """Request to audit a generated creative"""
    image_url: str
    expected_text: str
    style_constraints: Optional[str] = None


class AuditResponse(BaseModel):
    """Quality audit result"""
    passed: bool
    score: float
    issues: list[str]
    suggestions: list[str]


# --- Campaign Pipeline ---

class CampaignRequest(BaseModel):
    """Full campaign generation request"""
    client_id: Optional[str] = None
    business_name: str
    business_type: str
    language: Literal["punjabi", "hindi", "english"]
    template_type: Literal["festival", "offer", "product", "event"]
    occasion: Optional[str] = None
    brand_color: Optional[str] = "#FF6B35"
    count: int = Field(1, ge=1, le=5, description="Number of variations to generate")


class GeneratedPoster(BaseModel):
    """A single generated poster"""
    image_url: str
    headline: str
    subtext: str
    cta: str
    audit_score: Optional[float] = None
    audit_passed: Optional[bool] = None


class CampaignResponse(BaseModel):
    """Campaign generation result"""
    success: bool
    posters: list[GeneratedPoster]
    generation_time: float
