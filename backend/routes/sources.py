"""
Sources routes — upload, list, get, delete.
Handles document ingestion pipeline.
"""
import os
import uuid
import asyncio
import logging
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from database import get_db, Source, SourceChunk
from config import settings
from processing import process_document
from vector_store import vector_store

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {
    "pdf", "pptx", "ppt", "docx", "doc",
    "txt", "md",
    "mp4", "mov", "avi",
    "mp3", "wav", "m4a"
}

MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB


def get_source_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    type_map = {
        "pdf": "pdf", "pptx": "pptx", "ppt": "pptx",
        "docx": "docx", "doc": "docx",
        "txt": "text", "md": "text",
        "mp4": "video", "mov": "video", "avi": "video",
        "mp3": "audio", "wav": "audio", "m4a": "audio"
    }
    return type_map.get(ext, "text")


class SourceResponse(BaseModel):
    id: int
    name: str
    original_filename: str
    source_type: str
    file_size: int
    status: str
    error_message: Optional[str]
    is_demo: bool
    chunk_count: int = 0
    created_at: str

    class Config:
        from_attributes = True


async def run_processing_pipeline(source_id: int, file_path: str, source_name: str, source_type: str):
    """Background task: process document and index into vector store."""
    from database import AsyncSessionLocal, Source, SourceChunk
    async with AsyncSessionLocal() as db:
        try:
            # Mark as processing
            result = await db.execute(select(Source).where(Source.id == source_id))
            source = result.scalar_one_or_none()
            if not source:
                return
            source.status = "processing"
            await db.commit()

            # Process document
            chunks = process_document(file_path, source_id, source_name, source_type)

            # Store chunks in DB and vector store
            db_chunks = []
            texts = []
            metadatas = []

            for chunk_data in chunks:
                chroma_id = str(uuid.uuid4())
                db_chunk = SourceChunk(
                    source_id=source_id,
                    chunk_index=chunk_data.get("chunk_index", 0),
                    content=chunk_data.get("content", ""),
                    page_number=chunk_data.get("page_number"),
                    slide_number=chunk_data.get("slide_number"),
                    timestamp_start=chunk_data.get("timestamp_start"),
                    timestamp_end=chunk_data.get("timestamp_end"),
                    section_title=chunk_data.get("section_title"),
                    chroma_id=chroma_id,
                    metadata_=chunk_data.get("metadata", {})
                )
                db_chunks.append(db_chunk)
                texts.append(chunk_data["content"])
                meta = dict(chunk_data.get("metadata", {}))
                meta["chroma_id"] = chroma_id
                metadatas.append(meta)

            db.add_all(db_chunks)
            await db.flush()

            # Update chroma_ids after DB assigns IDs
            ids = [c.chroma_id for c in db_chunks]
            if texts:
                vector_store.add_chunks(texts, metadatas, ids)
            logger.info(f"Source {source_id}: indexed {len(texts)} chunks")

            # Mark as processed
            source.status = "processed"
            await db.commit()
            logger.info(f"Source {source_id} processing complete")

        except Exception as e:
            logger.error(f"Processing failed for source {source_id}: {e}")
            async with AsyncSessionLocal() as err_db:
                result = await err_db.execute(select(Source).where(Source.id == source_id))
                source = result.scalar_one_or_none()
                if source:
                    source.status = "error"
                    source.error_message = str(e)[:1000]
                    await err_db.commit()


@router.post("/upload")
async def upload_source(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload and queue a document for processing."""
    filename = file.filename or "unnamed_file"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type .{ext} not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read file
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 200 MB)")

    # Save to disk
    safe_name = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(settings.upload_dir, safe_name)
    with open(file_path, "wb") as f:
        f.write(content)

    source_type = get_source_type(filename)
    source_name = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()

    source = Source(
        name=source_name,
        original_filename=filename,
        source_type=source_type,
        file_path=file_path,
        file_size=len(content),
        status="pending",
        is_demo=False
    )
    db.add(source)
    await db.flush()
    source_id = source.id
    await db.commit()

    # Queue background processing
    background_tasks.add_task(
        run_processing_pipeline, source_id, file_path, source_name, source_type
    )

    return {
        "id": source_id,
        "name": source_name,
        "status": "pending",
        "message": "Upload successful. Processing started."
    }


@router.get("/")
async def list_sources(db: AsyncSession = Depends(get_db)):
    """List all sources."""
    result = await db.execute(select(Source).order_by(Source.created_at.desc()))
    sources = result.scalars().all()

    out = []
    for s in sources:
        chunk_result = await db.execute(
            select(SourceChunk).where(SourceChunk.source_id == s.id)
        )
        chunk_count = len(chunk_result.scalars().all())
        out.append({
            "id": s.id,
            "name": s.name,
            "original_filename": s.original_filename,
            "source_type": s.source_type,
            "file_size": s.file_size,
            "status": s.status,
            "error_message": s.error_message,
            "is_demo": s.is_demo,
            "chunk_count": chunk_count,
            "created_at": s.created_at.isoformat() if s.created_at else "",
        })
    return out


@router.get("/{source_id}")
async def get_source(source_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single source with its chunks."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    chunks_result = await db.execute(
        select(SourceChunk)
        .where(SourceChunk.source_id == source_id)
        .order_by(SourceChunk.chunk_index)
    )
    chunks = chunks_result.scalars().all()

    return {
        "id": source.id,
        "name": source.name,
        "original_filename": source.original_filename,
        "source_type": source.source_type,
        "file_size": source.file_size,
        "status": source.status,
        "error_message": source.error_message,
        "is_demo": source.is_demo,
        "created_at": source.created_at.isoformat() if source.created_at else "",
        "chunks": [
            {
                "id": c.id,
                "chunk_index": c.chunk_index,
                "content": c.content,
                "page_number": c.page_number,
                "slide_number": c.slide_number,
                "timestamp_start": c.timestamp_start,
                "timestamp_end": c.timestamp_end,
                "section_title": c.section_title,
            }
            for c in chunks
        ]
    }


@router.delete("/{source_id}")
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a source and all its chunks."""
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    # Remove from vector store
    vector_store.delete_by_source(source_id)

    # Delete file from disk
    if source.file_path and os.path.exists(source.file_path) and not source.is_demo:
        os.remove(source.file_path)

    # Delete from DB (cascade deletes chunks)
    await db.delete(source)

    return {"message": "Source deleted successfully"}


@router.get("/{source_id}/status")
async def get_source_status(source_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    chunk_result = await db.execute(
        select(SourceChunk).where(SourceChunk.source_id == source_id)
    )
    chunk_count = len(chunk_result.scalars().all())

    return {
        "id": source.id,
        "status": source.status,
        "chunk_count": chunk_count,
        "error_message": source.error_message
    }
