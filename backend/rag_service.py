"""
TutorForge AI — RAG Service
Retrieval-Augmented Generation for the AI Tutor.
"""
from __future__ import annotations
import logging
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from vector_store import vector_store
from ai_provider import llm_provider
from database import SourceChunk, Source, Citation, ChatMessage

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are TutorForge AI, an expert academic tutor. 
Your role is to help students understand course material using ONLY the provided context.

Rules:
1. Answer based on the provided context chunks from the student's uploaded materials.
2. Always cite your sources inline using [Source: <source_name>, <location>] notation.
3. If the context doesn't contain enough information, say so clearly.
4. Adapt your explanation style based on the student's request.
5. Be encouraging, precise, and academically rigorous.
6. Never fabricate citations or information.
"""


class RAGService:
    """Manages retrieval, context assembly, and LLM generation."""

    async def query(
        self,
        user_question: str,
        db: AsyncSession,
        n_chunks: int = 5,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Full RAG pipeline.
        Returns: {response, citations, retrieved_chunks}
        """
        # 1. Retrieve relevant chunks from vector store
        retrieved = vector_store.query(user_question, n_results=n_chunks)

        # 2. Load full chunk records from DB for citation metadata
        citations_data = []
        context_parts = []

        for r in retrieved:
            chroma_id = r["id"]
            chunk_meta = r["metadata"]

            # Try to load from DB
            source_id = chunk_meta.get("source_id")
            chunk_info = {
                "text": r["text"],
                "relevance": r["relevance"],
                "source_id": source_id,
                "source_name": chunk_meta.get("source_name", "Unknown"),
                "source_type": chunk_meta.get("source_type", "unknown"),
                "page_number": chunk_meta.get("page_number"),
                "slide_number": chunk_meta.get("slide_number"),
                "timestamp_start": chunk_meta.get("timestamp_start"),
                "timestamp_end": chunk_meta.get("timestamp_end"),
            }

            if source_id:
                try:
                    result = await db.execute(
                        select(SourceChunk).where(SourceChunk.chroma_id == chroma_id)
                    )
                    db_chunk = result.scalar_one_or_none()
                    if db_chunk:
                        chunk_info["chunk_db_id"] = db_chunk.id
                        chunk_info["page_number"] = db_chunk.page_number
                        chunk_info["slide_number"] = db_chunk.slide_number
                        chunk_info["timestamp_start"] = db_chunk.timestamp_start
                        chunk_info["timestamp_end"] = db_chunk.timestamp_end
                except Exception as e:
                    logger.warning(f"DB lookup failed for chunk {chroma_id}: {e}")

            # Format location string
            location = self._format_location(chunk_info)
            context_parts.append(
                f"[Source: {chunk_info['source_name']}, {location}]\n{r['text']}"
            )
            citations_data.append(chunk_info)

        # 3. Build context string
        context_str = "\n\n---\n\n".join(context_parts) if context_parts else ""

        # 4. Build messages for LLM
        system = SYSTEM_PROMPT
        if context_str:
            system += f"\n\nContext:\n{context_str}"
        else:
            system += (
                "\n\nNo source material has been uploaded yet. "
                "Tell the student to upload their course materials first, "
                "but you can still answer general questions."
            )

        messages = conversation_history[-6:] if conversation_history else []
        messages = [m for m in messages if m["role"] in ("user", "assistant")]
        messages.append({"role": "user", "content": user_question})

        # 5. Generate response
        try:
            response_text = llm_provider.chat(messages, system_prompt=system)
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            response_text = (
                f"I encountered an error generating a response: {str(e)[:200]}. "
                "Please check your AI provider configuration."
            )

        # 6. Format citations for frontend
        formatted_citations = [
            self._format_citation(c) for c in citations_data
            if c.get("relevance", 0) > 0.3
        ]

        return {
            "response": response_text,
            "citations": formatted_citations,
            "retrieved_chunks": len(retrieved),
            "context_used": bool(context_str)
        }

    def _format_location(self, chunk_info: Dict) -> str:
        """Build human-readable location string."""
        if chunk_info.get("timestamp_start") is not None:
            t_start = chunk_info["timestamp_start"]
            t_end = chunk_info.get("timestamp_end", t_start + 30)
            def fmt(s):
                m = int(s) // 60
                sec = int(s) % 60
                return f"{m:02d}:{sec:02d}"
            return f"{fmt(t_start)}–{fmt(t_end)}"
        elif chunk_info.get("page_number"):
            return f"Page {chunk_info['page_number']}"
        elif chunk_info.get("slide_number"):
            return f"Slide {chunk_info['slide_number']}"
        return "Section unknown"

    def _format_citation(self, chunk_info: Dict) -> Dict:
        """Format citation for API response."""
        return {
            "source_id": chunk_info.get("source_id"),
            "source_name": chunk_info.get("source_name", "Unknown"),
            "source_type": chunk_info.get("source_type", "unknown"),
            "location": self._format_location(chunk_info),
            "page_number": chunk_info.get("page_number"),
            "slide_number": chunk_info.get("slide_number"),
            "timestamp_start": chunk_info.get("timestamp_start"),
            "timestamp_end": chunk_info.get("timestamp_end"),
            "relevance": round(chunk_info.get("relevance", 0), 3),
            "excerpt": chunk_info.get("text", "")[:200] + "..." if len(chunk_info.get("text", "")) > 200 else chunk_info.get("text", ""),
        }


rag_service = RAGService()
