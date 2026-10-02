"""Search routes — semantic search across all knowledge."""
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from vector_store import vector_store

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    n_results: int = 10
    source_type: Optional[str] = None


@router.post("/")
async def semantic_search(body: SearchRequest):
    """Semantic search across all indexed chunks."""
    where = None
    if body.source_type:
        where = {"source_type": body.source_type}

    results = vector_store.query(
        body.query,
        n_results=body.n_results,
        where=where
    )

    return {
        "query": body.query,
        "results": [
            {
                "text": r["text"],
                "relevance": round(r["relevance"], 3),
                "source_name": r["metadata"].get("source_name", "Unknown"),
                "source_type": r["metadata"].get("source_type", "unknown"),
                "source_id": r["metadata"].get("source_id"),
                "page_number": r["metadata"].get("page_number"),
                "slide_number": r["metadata"].get("slide_number"),
                "timestamp_start": r["metadata"].get("timestamp_start"),
                "timestamp_end": r["metadata"].get("timestamp_end"),
            }
            for r in results
        ]
    }
