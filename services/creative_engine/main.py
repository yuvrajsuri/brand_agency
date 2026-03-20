"""
Creative Engine Service — FastAPI Application
Handles AI-powered campaign generation, copy writing, image generation, and quality auditing.
This is a standalone microservice that can be scaled independently.
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import sys
import asyncio

from routers import campaigns, copy, images, audit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Creative Engine Service",
    description="AI-powered campaign generation: copy, images, rendering orchestration, quality audit",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(campaigns.router)
app.include_router(copy.router)
app.include_router(images.router)
app.include_router(audit.router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "creative-engine",
        "version": "2.0.0"
    }


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )
