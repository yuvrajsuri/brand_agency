"""
Creative Engine Service Configuration
"""
import os


class Settings:
    """Service configuration from environment variables"""

    # Service
    SERVICE_NAME: str = "creative-engine"
    SERVICE_PORT: int = int(os.getenv("CREATIVE_ENGINE_PORT", "8001"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Internal service URLs
    RENDERER_URL: str = os.getenv("RENDERER_URL", "http://renderer:8002")
    POCKETBASE_URL: str = os.getenv("POCKETBASE_URL", "http://pocketbase:8090")

    # Gemini API
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"

    # Image Generation
    RUNWARE_API_KEY: str = os.getenv("RUNWARE_API_KEY", "")
    IMAGEN_MODEL: str = os.getenv("IMAGEN_MODEL", "imagen-4.0-generate-001")

    # Quality Audit
    AUDIT_PASS_THRESHOLD: float = float(os.getenv("AUDIT_PASS_THRESHOLD", "0.85"))
    AUDIT_MAX_RETRIES: int = int(os.getenv("AUDIT_MAX_RETRIES", "3"))

    # R2 Storage (for images generated before rendering)
    R2_ACCOUNT_ID: str = os.getenv("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET_NAME: str = os.getenv("R2_BUCKET_NAME", "brand-agency-creatives")
    R2_PUBLIC_DOMAIN: str = os.getenv("R2_PUBLIC_DOMAIN", "")


settings = Settings()
