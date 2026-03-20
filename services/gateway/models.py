"""
Gateway Service — Pydantic Models
"""
from typing import Optional, Any
from pydantic import BaseModel


class IncomingMessage(BaseModel):
    """Parsed WhatsApp message"""
    sender_phone: str
    sender_name: str
    message_type: str  # text | image | button | interactive
    message_text: str
    message_id: str
    timestamp: str
    context: Optional[dict] = None
    phone_number_id: str


class OutgoingTextMessage(BaseModel):
    """Request to send a WhatsApp text message"""
    to: str
    body: str
    preview_url: bool = False


class OutgoingImageMessage(BaseModel):
    """Request to send a WhatsApp image"""
    to: str
    image_url: str
    caption: Optional[str] = None


class IntentResult(BaseModel):
    """Intent classification result"""
    intent: str
    confidence: float
    language: str
    entities: dict = {}


class ClientRecord(BaseModel):
    """PocketBase client record"""
    id: Optional[str] = None
    business_name: str
    business_type: str
    phone: str
    language: str = "punjabi"
    brand_color: str = "#FF6B35"
    active: bool = True
