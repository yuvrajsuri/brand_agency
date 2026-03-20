"""
Gateway Service Configuration
"""
import os


class Settings:
    SERVICE_NAME: str = "gateway"
    SERVICE_PORT: int = int(os.getenv("GATEWAY_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Internal service URLs
    CREATIVE_ENGINE_URL: str = os.getenv("CREATIVE_ENGINE_URL", "http://creative-engine:8001")
    RENDERER_URL: str = os.getenv("RENDERER_URL", "http://renderer:8002")
    POCKETBASE_URL: str = os.getenv("POCKETBASE_URL", "http://pocketbase:8090")

    # Meta WhatsApp Cloud API
    META_ACCESS_TOKEN: str = os.getenv("META_ACCESS_TOKEN", "")
    META_PHONE_NUMBER_ID: str = os.getenv("META_PHONE_NUMBER_ID", "")
    META_VERIFY_TOKEN: str = os.getenv("META_VERIFY_TOKEN", "")

    # Gemini (for intent classification only)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"

    # Admin (for alerts)
    ADMIN_PHONE: str = os.getenv("ADMIN_PHONE", "")


settings = Settings()
