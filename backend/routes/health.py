"""Health check routes."""
from fastapi import APIRouter
from config import settings
from vector_store import vector_store

router = APIRouter()


@router.get("/health")
async def health_check():
    try:
        chunk_count = vector_store.count()
        vector_ok = True
    except Exception as e:
        chunk_count = 0
        vector_ok = False

    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "ai_provider": settings.ai_provider,
        "vector_store_chunks": chunk_count,
        "vector_store_ok": vector_ok,
    }
