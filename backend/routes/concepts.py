"""Concepts / knowledge graph routes."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db, Concept, ConceptRelationship, Mastery

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
async def list_concepts(
    student_id: str = "default_student",
    db: AsyncSession = Depends(get_db)
):
    """List all concepts with mastery scores."""
    result = await db.execute(select(Concept).order_by(Concept.subject, Concept.name))
    concepts = result.scalars().all()

    mastery_result = await db.execute(
        select(Mastery).where(Mastery.student_id == student_id)
    )
    masteries = {m.concept_id: m for m in mastery_result.scalars().all()}

    output = []
    for c in concepts:
        m = masteries.get(c.id)
        score = m.score if m else 0.0
        output.append({
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "parent_id": c.parent_id,
            "subject": c.subject,
            "is_demo": c.is_demo,
            "mastery": {
                "score": round(score, 3),
                "percentage": int(score * 100),
                "label": _mastery_label(score),
                "color": _mastery_color(score),
                "questions_seen": m.questions_seen if m else 0,
                "correct_answers": m.correct_answers if m else 0,
            }
        })
    return output


@router.get("/graph")
async def concept_graph(
    student_id: str = "default_student",
    db: AsyncSession = Depends(get_db)
):
    """Return graph data (nodes + edges) for the concept map."""
    result = await db.execute(select(Concept))
    concepts = result.scalars().all()

    rel_result = await db.execute(select(ConceptRelationship))
    relationships = rel_result.scalars().all()

    mastery_result = await db.execute(
        select(Mastery).where(Mastery.student_id == student_id)
    )
    masteries = {m.concept_id: m for m in mastery_result.scalars().all()}

    nodes = []
    for c in concepts:
        m = masteries.get(c.id)
        score = m.score if m else None   # None = unseen
        nodes.append({
            "id": c.id,
            "label": c.name,
            "description": c.description,
            "parent_id": c.parent_id,
            "subject": c.subject,
            "mastery_score": score,
            "mastery_pct": int(score * 100) if score is not None else None,
            "status": _mastery_status(score),
            "color": _mastery_color(score),
        })

    seen_edges = set()
    edges = []
    
    for r in relationships:
        edge_key = (r.source_concept_id, r.target_concept_id)
        if edge_key not in seen_edges:
            seen_edges.add(edge_key)
            edges.append({
                "source": r.source_concept_id,
                "target": r.target_concept_id,
                "type": r.relationship_type
            })

    # Also add parent→child edges
    for c in concepts:
        if c.parent_id:
            edge_key = (c.parent_id, c.id)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append({
                    "source": c.parent_id,
                    "target": c.id,
                    "type": "contains"
                })

    return {"nodes": nodes, "edges": edges}


@router.get("/{concept_id}")
async def get_concept(
    concept_id: int,
    student_id: str = "default_student",
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Concept).where(Concept.id == concept_id))
    concept = result.scalar_one_or_none()
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    mastery_result = await db.execute(
        select(Mastery).where(
            Mastery.concept_id == concept_id,
            Mastery.student_id == student_id
        )
    )
    mastery = mastery_result.scalar_one_or_none()
    score = mastery.score if mastery else 0.0

    return {
        "id": concept.id,
        "name": concept.name,
        "description": concept.description,
        "parent_id": concept.parent_id,
        "subject": concept.subject,
        "mastery": {
            "score": round(score, 3),
            "percentage": int(score * 100),
            "label": _mastery_label(score),
            "questions_seen": mastery.questions_seen if mastery else 0,
            "correct_answers": mastery.correct_answers if mastery else 0,
        }
    }


def _mastery_label(score: Optional[float]) -> str:
    if score is None:
        return "Not Started"
    if score >= 0.80:
        return "Mastered"
    elif score >= 0.55:
        return "Developing"
    elif score > 0.0:
        return "Needs Review"
    return "Not Started"


def _mastery_color(score: Optional[float]) -> str:
    if score is None:
        return "#3b82f6"    # blue = unseen
    if score >= 0.80:
        return "#22c55e"    # green
    elif score >= 0.55:
        return "#eab308"    # yellow
    elif score > 0.0:
        return "#f97316"    # orange
    return "#3b82f6"        # blue


def _mastery_status(score: Optional[float]) -> str:
    if score is None:
        return "unseen"
    if score >= 0.80:
        return "mastered"
    elif score >= 0.55:
        return "developing"
    elif score > 0.0:
        return "weak"
    return "unseen"
