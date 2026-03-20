"""
Renderer Service Configuration
"""
import os
from pathlib import Path


class Settings:
    """Service configuration from environment variables"""

    # Service
    SERVICE_NAME: str = "renderer"
    SERVICE_PORT: int = int(os.getenv("RENDERER_PORT", "8002"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # R2 Storage
    R2_ACCOUNT_ID: str = os.getenv("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET_NAME: str = os.getenv("R2_BUCKET_NAME", "brand-agency-creatives")
    R2_PUBLIC_DOMAIN: str = os.getenv("R2_PUBLIC_DOMAIN", "")

    # Local storage fallback
    LOCAL_STORAGE_DIR: str = os.getenv("LOCAL_STORAGE_DIR", "")

    # Temp directory for Playwright renders
    TEMP_DIR: Path = Path(os.getenv("TEMP_DIR", "/tmp/overlay-engine"))


settings = Settings()
