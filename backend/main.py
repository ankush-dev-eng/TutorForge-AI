"""
TutorForge AI — FastAPI Application Entry Point
"""
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from database import init_db
from fastapi.responses import JSONResponse
from ai_provider import ProviderError

# Routes
from routes import (
    sources, chat, assessment, concepts, analytics,
    learning_path, search, health
)

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("TutorForge AI starting up...")
    await init_db()
    logger.info("Database initialized")

    # Seed demo data if DB is empty
    from seed import seed_demo_data
    await seed_demo_data()
    logger.info("Demo data seeded")

    yield
    # Shutdown
    logger.info("TutorForge AI shutting down...")


app = FastAPI(
    title="TutorForge AI API",
    description="Personalized AI tutoring platform with multimodal knowledge ingestion",
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(ProviderError)
async def provider_error_handler(request, exc: ProviderError):
    code = exc.code
    if code == "AUTHENTICATION_ERROR":
        msg = "AI authentication failed. Check the configured provider."
    elif code == "MODEL_UNAVAILABLE":
        msg = "The AI model is temporarily unavailable. TutorForge is trying another model."
    elif code == "RATE_LIMIT":
        msg = "AI usage is temporarily limited. Please try again."
    elif code == "TIMEOUT":
        msg = "The AI response took too long. Please try again."
    elif code == "CONFIGURATION_ERROR":
        msg = "The AI provider is not configured."
    else:
        msg = "TutorForge could not generate a response right now."
        
    return JSONResponse(
        status_code=503 if code in ["MODEL_UNAVAILABLE", "TIMEOUT"] else 400,
        content={"detail": msg, "error_type": code}
    )

# Mount uploads for static serving
if os.path.exists(settings.upload_dir):
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(assessment.router, prefix="/api/assessment", tags=["assessment"])
app.include_router(concepts.router, prefix="/api/concepts", tags=["concepts"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(learning_path.router, prefix="/api/learning-path", tags=["learning-path"])
app.include_router(search.router, prefix="/api/search", tags=["search"])


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs"
    }
