"""
TutorForge AI — Learning Path Generator
Creates personalized daily study plans based on mastery data.
"""
from __future__ import annotations
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import Mastery, Concept, Source, LearningPath

logger = logging.getLogger(__name__)

MASTERY_MASTERED = 0.80
MASTERY_DEVELOPING = 0.55
MASTERY_WEAK = 0.0


class LearningPathService:

    async def generate(
        self,
        student_id: str,
        db: AsyncSession,
        max_items: int = 8
    ) -> Dict[str, Any]:
        """Generate a personalized learning path."""

        # Load all masteries with concept info
        result = await db.execute(
            select(Mastery)
            .options(selectinload(Mastery.concept))
            .where(Mastery.student_id == student_id)
        )
        masteries = result.scalars().all()

        # Load available sources
        src_result = await db.execute(select(Source).where(Source.status == "processed"))
        sources = src_result.scalars().all()

        # Load all concepts for unseen ones
        all_concepts_result = await db.execute(select(Concept))
        all_concepts = all_concepts_result.scalars().all()

        mastery_map = {m.concept_id: m for m in masteries}
        seen_concept_ids = set(mastery_map.keys())

        # Categorize concepts
        weak = []
        developing = []
        mastered = []
        unseen = []

        for concept in all_concepts:
            m = mastery_map.get(concept.id)
            if m is None:
                unseen.append(concept)
            elif m.score < 0.55:
                weak.append((concept, m))
            elif m.score < 0.80:
                developing.append((concept, m))
            else:
                mastered.append((concept, m))

        # Prioritize: weak → developing → unseen
        items = []
        today = datetime.utcnow()

        # Weak concepts → Review + Quiz
        for concept, m in weak[:2]:
            pct = int(m.score * 100)
            items.append({
                "type": "review",
                "title": f"Review: {concept.name}",
                "description": f"Your mastery is {pct}% — this needs attention",
                "duration_minutes": 15,
                "concept_id": concept.id,
                "concept_name": concept.name,
                "mastery_score": m.score,
                "priority": "high",
                "icon": "BookOpen"
            })
            items.append({
                "type": "quiz",
                "title": f"Practice Quiz: {concept.name}",
                "description": f"5 adaptive questions to strengthen understanding",
                "duration_minutes": 10,
                "concept_id": concept.id,
                "concept_name": concept.name,
                "mastery_score": m.score,
                "priority": "high",
                "icon": "Target"
            })

        # Developing concepts → Short review
        for concept, m in developing[:1]:
            pct = int(m.score * 100)
            items.append({
                "type": "review",
                "title": f"Strengthen: {concept.name}",
                "description": f"Mastery at {pct}% — almost there!",
                "duration_minutes": 10,
                "concept_id": concept.id,
                "concept_name": concept.name,
                "mastery_score": m.score,
                "priority": "medium",
                "icon": "TrendingUp"
            })

        # Unseen concepts → Introduce
        for concept in unseen[:2]:
            items.append({
                "type": "learn",
                "title": f"Learn: {concept.name}",
                "description": "New concept — start here to build your knowledge",
                "duration_minutes": 20,
                "concept_id": concept.id,
                "concept_name": concept.name,
                "mastery_score": 0.0,
                "priority": "medium",
                "icon": "Sparkles"
            })

        # Add source-linked activities if sources exist
        video_sources = [s for s in sources if s.source_type in ("mp4", "mov", "video")]
        if video_sources and len(items) < max_items:
            s = video_sources[0]
            items.append({
                "type": "watch",
                "title": f"Watch: {s.name}",
                "description": "Review lecture material",
                "duration_minutes": 20,
                "source_id": s.id,
                "source_name": s.name,
                "priority": "low",
                "icon": "Play"
            })

        # Mastery review for highest mastered
        if mastered:
            concept, m = mastered[0]
            items.append({
                "type": "challenge",
                "title": f"Challenge: {concept.name}",
                "description": "You're strong here — try hard-level questions",
                "duration_minutes": 8,
                "concept_id": concept.id,
                "concept_name": concept.name,
                "mastery_score": m.score,
                "priority": "low",
                "icon": "Zap"
            })

        # Limit and add ordering
        items = items[:max_items]
        for i, item in enumerate(items):
            item["order"] = i + 1
            item["completed"] = False

        path_data = {
            "generated_at": today.isoformat(),
            "total_time_minutes": sum(i.get("duration_minutes", 0) for i in items),
            "items": items,
            "summary": {
                "weak_count": len(weak),
                "developing_count": len(developing),
                "mastered_count": len(mastered),
                "unseen_count": len(unseen)
            }
        }

        # Persist
        result = await db.execute(
            select(LearningPath).where(LearningPath.student_id == student_id)
        )
        lp = result.scalar_one_or_none()
        if lp:
            lp.generated_at = today
            lp.items = items
        else:
            lp = LearningPath(student_id=student_id, items=items)
            db.add(lp)

        return path_data


learning_path_service = LearningPathService()
