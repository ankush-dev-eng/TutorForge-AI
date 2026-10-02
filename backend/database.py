"""
TutorForge AI — SQLAlchemy Database Models
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime,
    ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from config import settings


engine = create_async_engine(settings.database_url, echo=settings.debug)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────
# Source / Document models
# ──────────────────────────────────────────

class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    source_type = Column(String(50), nullable=False)   # pdf|pptx|video|audio|text|docx
    file_path = Column(String(1000))
    file_size = Column(Integer, default=0)
    status = Column(String(50), default="pending")     # pending|processing|processed|error
    error_message = Column(Text)
    is_demo = Column(Boolean, default=False)
    metadata_ = Column("metadata", JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chunks = relationship("SourceChunk", back_populates="source", cascade="all, delete-orphan")
    citations = relationship("Citation", back_populates="source", cascade="all, delete-orphan")


class SourceChunk(Base):
    __tablename__ = "source_chunks"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    chunk_index = Column(Integer, default=0)
    content = Column(Text, nullable=False)
    # Provenance metadata
    page_number = Column(Integer)
    slide_number = Column(Integer)
    timestamp_start = Column(Float)    # seconds
    timestamp_end = Column(Float)      # seconds
    section_title = Column(String(500))
    chroma_id = Column(String(100))    # ID in ChromaDB
    metadata_ = Column("metadata", JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Source", back_populates="chunks")


# ──────────────────────────────────────────
# Concept / Knowledge Graph
# ──────────────────────────────────────────

class Concept(Base):
    __tablename__ = "concepts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    parent_id = Column(Integer, ForeignKey("concepts.id"), nullable=True)
    subject = Column(String(200), default="General")
    is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    children = relationship("Concept", back_populates="parent")
    parent = relationship("Concept", back_populates="children", remote_side="Concept.id")
    masteries = relationship("Mastery", back_populates="concept", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="concept", cascade="all, delete-orphan")


class ConceptRelationship(Base):
    __tablename__ = "concept_relationships"

    id = Column(Integer, primary_key=True, index=True)
    source_concept_id = Column(Integer, ForeignKey("concepts.id"), nullable=False)
    target_concept_id = Column(Integer, ForeignKey("concepts.id"), nullable=False)
    relationship_type = Column(String(100), default="relates_to")   # prerequisite|relates_to|contains


# ──────────────────────────────────────────
# Mastery Tracking
# ──────────────────────────────────────────

class Mastery(Base):
    __tablename__ = "masteries"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(100), default="default_student")
    concept_id = Column(Integer, ForeignKey("concepts.id"), nullable=False)
    score = Column(Float, default=0.0)          # 0.0 – 1.0
    questions_seen = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)

    concept = relationship("Concept", back_populates="masteries")
    history = relationship("MasteryHistory", back_populates="mastery", cascade="all, delete-orphan")


class MasteryHistory(Base):
    __tablename__ = "mastery_history"

    id = Column(Integer, primary_key=True, index=True)
    mastery_id = Column(Integer, ForeignKey("masteries.id"), nullable=False)
    score = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    mastery = relationship("Mastery", back_populates="history")


# ──────────────────────────────────────────
# Assessment / Quiz
# ──────────────────────────────────────────

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id"), nullable=True)
    question_type = Column(String(50), default="mcq")   # mcq|true_false|short_answer|scenario
    difficulty = Column(Integer, default=2)              # 1=easy 2=medium 3=hard
    text = Column(Text, nullable=False)
    options = Column(JSON)               # list of strings for MCQ
    correct_answer = Column(Text)
    explanation = Column(Text)
    source_chunk_ids = Column(JSON, default=[])
    is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    concept = relationship("Concept", back_populates="questions")
    responses = relationship("AssessmentResponse", back_populates="question", cascade="all, delete-orphan")


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(100), default="default_student")
    concept_id = Column(Integer, ForeignKey("concepts.id"), nullable=True)
    title = Column(String(500))
    status = Column(String(50), default="in_progress")   # in_progress|completed
    current_difficulty = Column(Integer, default=2)
    total_questions = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    responses = relationship("AssessmentResponse", back_populates="assessment", cascade="all, delete-orphan")


class AssessmentResponse(Base):
    __tablename__ = "assessment_responses"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    student_answer = Column(Text)
    is_correct = Column(Boolean)
    confidence = Column(Integer, default=3)   # 1-5
    time_spent = Column(Integer, default=0)   # seconds
    mastery_before = Column(Float)
    mastery_after = Column(Float)
    next_difficulty = Column(Integer)
    answered_at = Column(DateTime, default=datetime.utcnow)

    assessment = relationship("Assessment", back_populates="responses")
    question = relationship("Question", back_populates="responses")


# ──────────────────────────────────────────
# AI Tutor Chat
# ──────────────────────────────────────────

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(100), default="default_student")
    title = Column(String(500), default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)    # user|assistant
    content = Column(Text, nullable=False)
    citations = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


# ──────────────────────────────────────────
# Citation
# ──────────────────────────────────────────

class Citation(Base):
    __tablename__ = "citations"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    chunk_id = Column(Integer, ForeignKey("source_chunks.id"), nullable=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=True)
    relevance_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Source", back_populates="citations")


# ──────────────────────────────────────────
# Learning Path
# ──────────────────────────────────────────

class LearningPath(Base):
    __tablename__ = "learning_paths"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(100), default="default_student")
    generated_at = Column(DateTime, default=datetime.utcnow)
    items = Column(JSON, default=[])    # list of LearningPathItem dicts


# ──────────────────────────────────────────
# Study Session Analytics
# ──────────────────────────────────────────

class StudySession(Base):
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(100), default="default_student")
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    duration_minutes = Column(Float, default=0)
    activity_type = Column(String(100))   # chat|quiz|reading|review


# ──────────────────────────────────────────
# DB helpers
# ──────────────────────────────────────────

async def init_db():
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency for FastAPI routes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
