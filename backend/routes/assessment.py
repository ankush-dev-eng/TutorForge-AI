"""Adaptive Assessment routes."""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db, Assessment, AssessmentResponse, Question, Concept, Mastery
from assessment_service import assessment_service

router = APIRouter()
logger = logging.getLogger(__name__)


class StartAssessmentRequest(BaseModel):
    concept_id: Optional[int] = None
    student_id: str = "default_student"
    question_type: str = "mcq"   # mcq|true_false|short_answer


class SubmitAnswerRequest(BaseModel):
    assessment_id: int
    question_id: int
    answer: str
    confidence: int = 3   # 1-5
    time_spent: int = 0   # seconds
    student_id: str = "default_student"


@router.post("/start")
async def start_assessment(body: StartAssessmentRequest, db: AsyncSession = Depends(get_db)):
    """Start a new adaptive assessment for a concept."""
    # Get concept
    if body.concept_id:
        result = await db.execute(select(Concept).where(Concept.id == body.concept_id))
        concept = result.scalar_one_or_none()
        if not concept:
            raise HTTPException(status_code=404, detail="Concept not found")
    else:
        # Pick weakest concept
        result = await db.execute(
            select(Mastery)
            .options(selectinload(Mastery.concept))
            .where(Mastery.student_id == body.student_id)
            .order_by(Mastery.score.asc())
        )
        weakest = result.scalars().first()
        if weakest:
            concept = weakest.concept
        else:
            # Fall back to first concept
            result = await db.execute(select(Concept).limit(1))
            concept = result.scalar_one_or_none()
            if not concept:
                raise HTTPException(status_code=404, detail="No concepts found. Please seed demo data.")

    # Get current mastery
    mastery = await assessment_service.get_or_create_mastery(concept.id, body.student_id, db)
    initial_difficulty = assessment_service.select_next_difficulty(mastery.score, 2)

    # Create assessment
    assessment = Assessment(
        student_id=body.student_id,
        concept_id=concept.id,
        title=f"Adaptive Quiz: {concept.name}",
        status="in_progress",
        current_difficulty=initial_difficulty
    )
    db.add(assessment)
    await db.flush()
    assessment_id = assessment.id

    # Generate first question
    question = await assessment_service.generate_question(
        concept, initial_difficulty, body.question_type, db
    )

    if question.id is None:
        db.add(question)
        await db.flush()

    return {
        "assessment_id": assessment_id,
        "concept": {"id": concept.id, "name": concept.name},
        "question": _format_question(question, initial_difficulty),
        "mastery_before": mastery.score,
        "difficulty": initial_difficulty,
        "difficulty_label": assessment_service.difficulty_label(initial_difficulty)
    }


@router.post("/submit")
async def submit_answer(body: SubmitAnswerRequest, db: AsyncSession = Depends(get_db)):
    """Submit an answer and get feedback + next question."""
    # Load assessment
    result = await db.execute(select(Assessment).where(Assessment.id == body.assessment_id))
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    # Load question
    result = await db.execute(select(Question).where(Question.id == body.question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Evaluate answer
    eval_result = await assessment_service.evaluate_answer(question, body.answer)
    is_correct = eval_result["is_correct"]

    # Update mastery
    mastery = await assessment_service.get_or_create_mastery(
        assessment.concept_id, body.student_id, db
    )
    mastery_before = mastery.score
    mastery_after = await assessment_service.update_mastery(
        mastery, is_correct, assessment.current_difficulty, db
    )

    # Update assessment stats
    assessment.total_questions += 1
    if is_correct:
        assessment.correct_count = (assessment.correct_count or 0) + 1

    # Determine next difficulty
    next_difficulty = assessment_service.select_next_difficulty(mastery_after, assessment.current_difficulty)
    assessment.current_difficulty = next_difficulty

    # Save response record
    response = AssessmentResponse(
        assessment_id=assessment.id,
        question_id=question.id,
        student_answer=body.answer,
        is_correct=is_correct,
        confidence=body.confidence,
        time_spent=body.time_spent,
        mastery_before=mastery_before,
        mastery_after=mastery_after,
        next_difficulty=next_difficulty
    )
    db.add(response)

    # Load concept for next question
    result = await db.execute(select(Concept).where(Concept.id == assessment.concept_id))
    concept = result.scalar_one_or_none()

    # Generate next question
    existing_qids_result = await db.execute(
        select(AssessmentResponse.question_id).where(AssessmentResponse.assessment_id == assessment.id)
    )
    exclude_ids = [r[0] for r in existing_qids_result.all()]

    next_question = None
    if concept:
        next_question = await assessment_service.generate_question(
            concept, next_difficulty, question.question_type, db, exclude_ids=exclude_ids
        )
        if next_question and next_question.id is None:
            db.add(next_question)
            await db.flush()

    mastery_label = "Mastered" if mastery_after >= 0.8 else ("Developing" if mastery_after >= 0.55 else "Needs Review")

    return {
        "is_correct": is_correct,
        "feedback": eval_result["feedback"],
        "correct_answer": question.correct_answer,
        "explanation": question.explanation or "",
        "mastery_before": round(mastery_before, 3),
        "mastery_after": round(mastery_after, 3),
        "mastery_label": mastery_label,
        "next_difficulty": next_difficulty,
        "next_difficulty_label": assessment_service.difficulty_label(next_difficulty),
        "next_question": _format_question(next_question, next_difficulty) if next_question else None,
        "total_questions": assessment.total_questions,
        "correct_count": assessment.correct_count or 0,
        "source_chunks": question.source_chunk_ids or []
    }


@router.post("/{assessment_id}/complete")
async def complete_assessment(assessment_id: int, db: AsyncSession = Depends(get_db)):
    """Mark assessment as complete and return summary."""
    from datetime import datetime
    result = await db.execute(
        select(Assessment)
        .options(selectinload(Assessment.responses))
        .where(Assessment.id == assessment_id)
    )
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    assessment.status = "completed"
    assessment.completed_at = datetime.utcnow()

    responses = assessment.responses
    correct = sum(1 for r in responses if r.is_correct)
    accuracy = correct / len(responses) if responses else 0

    concept_result = await db.execute(select(Concept).where(Concept.id == assessment.concept_id))
    concept = concept_result.scalar_one_or_none()

    mastery_result = await db.execute(
        select(Mastery).where(
            Mastery.concept_id == assessment.concept_id,
            Mastery.student_id == assessment.student_id
        )
    )
    mastery = mastery_result.scalar_one_or_none()

    return {
        "assessment_id": assessment_id,
        "concept_name": concept.name if concept else "Unknown",
        "total_questions": len(responses),
        "correct": correct,
        "accuracy": round(accuracy, 3),
        "final_mastery": round(mastery.score if mastery else 0, 3),
        "mastery_label": _mastery_label(mastery.score if mastery else 0),
        "next_steps": _generate_next_steps(accuracy, concept)
    }


@router.get("/history")
async def assessment_history(student_id: str = "default_student", db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Assessment)
        .where(Assessment.student_id == student_id)
        .order_by(Assessment.started_at.desc())
    )
    assessments = result.scalars().all()
    return [
        {
            "id": a.id,
            "concept_id": a.concept_id,
            "title": a.title,
            "status": a.status,
            "total_questions": a.total_questions,
            "correct_count": a.correct_count,
            "started_at": a.started_at.isoformat() if a.started_at else "",
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        }
        for a in assessments
    ]


def _format_question(q: Optional[Question], difficulty: int) -> Optional[dict]:
    if not q:
        return None
    return {
        "id": q.id,
        "text": q.text,
        "question_type": q.question_type,
        "options": q.options or [],
        "difficulty": difficulty,
        "difficulty_label": assessment_service.difficulty_label(difficulty),
    }


def _mastery_label(score: float) -> str:
    if score >= 0.8:
        return "Mastered"
    elif score >= 0.55:
        return "Developing"
    return "Needs Review"


def _generate_next_steps(accuracy: float, concept: Optional[Concept]) -> List[str]:
    name = concept.name if concept else "this topic"
    if accuracy >= 0.8:
        return [f"Great work! Try harder questions on {name}.", "Explore related advanced topics."]
    elif accuracy >= 0.5:
        return [f"Review key concepts in {name}.", "Try 5 more medium-difficulty questions."]
    else:
        return [f"Re-read the core material on {name}.", "Ask the AI tutor for a simplified explanation.", "Take another quiz when ready."]
