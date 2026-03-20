"""
Gateway Service — FastAPI Application
Entry point for all external traffic: WhatsApp webhooks, client API, routing.
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import sys
import asyncio

from routers import whatsapp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Gateway Service",
    description="WhatsApp webhook handler, client routing, and B2C chatbot",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(whatsapp.router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "gateway",
        "version": "2.0.0"
    }


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
