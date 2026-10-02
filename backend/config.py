"""
TutorForge AI — Configuration
Loads settings from environment variables / .env file.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List


class Settings(BaseSettings):
    # App
    app_name: str = "TutorForge AI"
    app_version: str = "1.0.0"
    debug: bool = True

    # AI Provider
    ai_provider: str = "local"          # "gemini" | "openai" | "local"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_fallback_model: str = "gemini-3.7-flash"     # leave empty to disable fallback model
    gemini_secondary_fallback_model: str = "gemini-3.6-flash"
    openai_api_key: str = ""

    # Embedding
    embedding_provider: str = "local"   # "local" | "gemini" | "openai"

    # Database
    database_url: str = "sqlite+aiosqlite:///./tutorforge.db"

    # Vector Store
    vector_store_backend: str = "local"    # "local" | "chroma"
    local_vs_path: str = ""                # path for LocalVectorStore JSON persistence (empty = in-memory)

    # ChromaDB (only used when vector_store_backend = "chroma")
    chroma_persist_dir: str = "./chroma_db"

    # Uploads
    upload_dir: str = "./uploads"

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Whisper
    whisper_model: str = "base"

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    def ensure_dirs(self):
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        if self.vector_store_backend == "chroma":
            Path(self.chroma_persist_dir).mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
