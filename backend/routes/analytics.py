"""Analytics routes."""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import (
    get_db, Mastery, MasteryHistory, Concept,
    AssessmentResponse, Assessment, StudySession
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/dashboard")
async def dashboard_analytics(
    student_id: str = "default_student",
    db: AsyncSession = Depends(get_db)
):
    """Aggregate analytics for dashboard."""
    # Mastery stats
    mastery_result = await db.execute(
        select(Mastery).where(Mastery.student_id == student_id)
    )
    masteries = mastery_result.scalars().all()

    total_concepts = len(masteries)
    mastered_count = sum(1 for m in masteries if m.score >= 0.80)
    overall_mastery = sum(m.score for m in masteries) / max(total_concepts, 1)

    # Assessment stats
    resp_result = await db.execute(
        select(AssessmentResponse)
        .join(Assessment)
        .where(Assessment.student_id == student_id)
    )
    responses = resp_result.scalars().all()
    total_questions = len(responses)
    correct_count = sum(1 for r in responses if r.is_correct)
    accuracy = correct_count / max(total_questions, 1)

    # Study time (from study sessions or estimate from assessments)
    study_result = await db.execute(
        select(StudySession).where(StudySession.student_id == student_id)
    )
    sessions = study_result.scalars().all()
    study_time_minutes = sum(s.duration_minutes for s in sessions if s.duration_minutes)

    # Streak (days with activity in last 30)
    streak = _calculate_streak(responses)

    # Top masteries
    concepts_result = await db.execute(select(Concept))
    all_concepts = {c.id: c for c in concepts_result.scalars().all()}

    mastery_list = []
    for m in sorted(masteries, key=lambda x: x.score, reverse=True):
        concept = all_concepts.get(m.concept_id)
        if concept:
            mastery_list.append({
                "concept_id": m.concept_id,
                "concept_name": concept.name,
                "score": round(m.score, 3),
                "percentage": int(m.score * 100),
                "label": _mastery_label(m.score),
                "questions_seen": m.questions_seen,
                "correct_answers": m.correct_answers,
            })

    return {
        "overall_mastery": round(overall_mastery, 3),
        "overall_mastery_pct": int(overall_mastery * 100),
        "mastered_concepts": mastered_count,
        "total_concepts_attempted": total_concepts,
        "total_questions_answered": total_questions,
        "correct_count": correct_count,
        "accuracy": round(accuracy, 3),
        "accuracy_pct": int(accuracy * 100),
        "study_time_minutes": round(study_time_minutes),
        "streak_days": streak,
        "concept_masteries": mastery_list,
    }


@router.get("/mastery-history")
async def mastery_history(
    student_id: str = "default_student",
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Return mastery history for charting."""
    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(MasteryHistory)
        .join(Mastery)
        .where(
            Mastery.student_id == student_id,
            MasteryHistory.recorded_at >= since
        )
        .order_by(MasteryHistory.recorded_at.asc())
    )
    history = result.scalars().all()

    # Group by day
    day_scores: dict = {}
    for h in history:
        day = h.recorded_at.strftime("%Y-%m-%d")
        if day not in day_scores:
            day_scores[day] = []
        day_scores[day].append(h.score)

    chart_data = [
        {"date": day, "mastery": round(sum(scores) / len(scores), 3)}
        for day, scores in sorted(day_scores.items())
    ]

    return {"history": chart_data}


@router.get("/performance")
async def performance_stats(
    student_id: str = "default_student",
    db: AsyncSession = Depends(get_db)
):
    """Per-concept performance breakdown."""
    resp_result = await db.execute(
        select(AssessmentResponse)
        .join(Assessment)
        .where(Assessment.student_id == student_id)
    )
    responses = resp_result.scalars().all()

    # Group by assessment → concept
    assess_result = await db.execute(
        select(Assessment).where(Assessment.student_id == student_id)
    )
    assess_map = {a.id: a for a in assess_result.scalars().all()}

    concepts_result = await db.execute(select(Concept))
    concepts_map = {c.id: c for c in concepts_result.scalars().all()}

    concept_perf: dict = {}
    for r in responses:
        assessment = assess_map.get(r.assessment_id)
        if not assessment or not assessment.concept_id:
            continue
        cid = assessment.concept_id
        if cid not in concept_perf:
            concept = concepts_map.get(cid)
            concept_perf[cid] = {
                "concept_id": cid,
                "concept_name": concept.name if concept else "Unknown",
                "total": 0,
                "correct": 0,
                "easy": 0,
                "medium": 0,
                "hard": 0,
            }
        concept_perf[cid]["total"] += 1
        if r.is_correct:
            concept_perf[cid]["correct"] += 1

    result_list = []
    for cid, data in concept_perf.items():
        acc = data["correct"] / max(data["total"], 1)
        result_list.append({
            **data,
            "accuracy": round(acc, 3),
            "accuracy_pct": int(acc * 100),
        })

    return sorted(result_list, key=lambda x: x["accuracy"])


@router.get("/insights")
async def insights(
    student_id: str = "default_student",
    db: AsyncSession = Depends(get_db)
):
    """Generate text insights based on actual student data."""
    mastery_result = await db.execute(
        select(Mastery)
        .where(Mastery.student_id == student_id)
    )
    masteries = mastery_result.scalars().all()
    concepts_result = await db.execute(select(Concept))
    concepts_map = {c.id: c for c in concepts_result.scalars().all()}

    if not masteries:
        return {"insights": ["Upload your course materials and complete a quiz to see personalized insights."]}

    insights_list = []

    weakest = min(masteries, key=lambda m: m.score)
    strongest = max(masteries, key=lambda m: m.score)

    if weakest.score < 0.55:
        name = concepts_map.get(weakest.concept_id, type("C", (), {"name": "Unknown"})()).name
        insights_list.append(f"⚠️ {name} is your weakest area at {int(weakest.score * 100)}%. Focus here first.")

    if strongest.score >= 0.8:
        name = concepts_map.get(strongest.concept_id, type("C", (), {"name": "Unknown"})()).name
        insights_list.append(f"✅ Excellent mastery of {name} at {int(strongest.score * 100)}%.")

    # High questions_seen but low accuracy
    for m in masteries:
        if m.questions_seen >= 5 and m.correct_answers / max(m.questions_seen, 1) < 0.4:
            name = concepts_map.get(m.concept_id, type("C", (), {"name": "Unknown"})()).name
            insights_list.append(f"📉 You've attempted many questions on {name} but accuracy is low. Try reviewing the material first.")

    if not insights_list:
        insights_list.append("Keep practicing! Your insights will appear as you complete more quizzes.")

    return {"insights": insights_list}


def _calculate_streak(responses: list) -> int:
    if not responses:
        return 0
    dates = sorted({r.answered_at.date() for r in responses if r.answered_at}, reverse=True)
    if not dates:
        return 0
    today = datetime.utcnow().date()
    if dates[0] < today - timedelta(days=1):
        return 0
    streak = 0
    prev = today
    for d in dates:
        if (prev - d).days <= 1:
            streak += 1
            prev = d
        else:
            break
    return streak


def _mastery_label(score: float) -> str:
    if score >= 0.80:
        return "Mastered"
    elif score >= 0.55:
        return "Developing"
    elif score > 0:
        return "Needs Review"
    return "Not Started"
