"""Chat / AI Tutor routes."""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db, ChatSession, ChatMessage
from rag_service import rag_service

router = APIRouter()
logger = logging.getLogger(__name__)


class MessageRequest(BaseModel):
    content: str
    session_id: Optional[int] = None
    student_id: str = "default_student"


class SessionCreate(BaseModel):
    title: str = "New Chat"
    student_id: str = "default_student"


@router.post("/sessions")
async def create_session(body: SessionCreate, db: AsyncSession = Depends(get_db)):
    session = ChatSession(title=body.title, student_id=body.student_id)
    db.add(session)
    await db.flush()
    return {"id": session.id, "title": session.title, "created_at": session.created_at.isoformat()}


@router.get("/sessions")
async def list_sessions(student_id: str = "default_student", db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.student_id == student_id)
        .order_by(ChatSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [
        {"id": s.id, "title": s.title, "created_at": s.created_at.isoformat()}
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "citations": m.citations or [],
            "created_at": m.created_at.isoformat()
        }
        for m in messages
    ]


@router.post("/message")
async def send_message(body: MessageRequest, db: AsyncSession = Depends(get_db)):
    """
    Send a message to the AI tutor and get a response with citations.
    """
    # Get or create session
    session_id = body.session_id
    if not session_id:
        session = ChatSession(
            title=body.content[:60] + "..." if len(body.content) > 60 else body.content,
            student_id=body.student_id
        )
        db.add(session)
        await db.flush()
        session_id = session.id

    # Load conversation history
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    history = history_result.scalars().all()
    conversation_history = [{"role": m.role, "content": m.content} for m in history]

    # Save user message
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=body.content,
        citations=[]
    )
    db.add(user_msg)
    await db.flush()

    # Run RAG
    rag_result = await rag_service.query(
        body.content,
        db,
        n_chunks=5,
        conversation_history=conversation_history
    )

    # Save assistant message
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=rag_result["response"],
        citations=rag_result["citations"]
    )
    db.add(assistant_msg)
    await db.flush()

    return {
        "session_id": session_id,
        "message_id": assistant_msg.id,
        "response": rag_result["response"],
        "citations": rag_result["citations"],
        "retrieved_chunks": rag_result["retrieved_chunks"],
        "context_used": rag_result["context_used"]
    }


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    return {"message": "Session deleted"}
