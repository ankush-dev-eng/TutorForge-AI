"""
TutorForge AI — Adaptive Assessment Service
Manages question generation, answer evaluation, mastery tracking,
and the adaptive next-question selection algorithm.
"""
from __future__ import annotations
import logging
import json
import re
import math
import random
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from database import (
    Question, Assessment, AssessmentResponse, Mastery, MasteryHistory, Concept
)
from ai_provider import llm_provider
from rag_service import rag_service

logger = logging.getLogger(__name__)

# Mastery update constants
MASTERY_CORRECT_WEIGHT = 0.15    # how much a correct answer boosts mastery
MASTERY_WRONG_WEIGHT = 0.08      # how much a wrong answer decreases mastery
DIFFICULTY_UP_THRESHOLD = 0.75   # mastery above this → increase difficulty
DIFFICULTY_DOWN_THRESHOLD = 0.45 # mastery below this → decrease difficulty


QUESTION_GEN_PROMPT = """You are an expert academic question generator.
Generate a {question_type} question about "{concept}" at {difficulty} difficulty.
Use this context if available:
{context}

Return ONLY valid JSON with this exact structure:
{{
  "text": "Question text here",
  "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
  "correct_answer": "A) ...",
  "explanation": "Why this is correct, explained clearly for a student."
}}

For true_false questions, options should be ["True", "False"].
For short_answer, options should be [].
Ensure explanations cite the relevant concept.
"""

EVAL_PROMPT = """You are evaluating a student's answer to a short-answer question.

Question: {question}
Expected answer (key points): {correct_answer}
Student's answer: {student_answer}

Respond with ONLY valid JSON:
{{
  "is_correct": true or false,
  "score": 0.0 to 1.0,
  "feedback": "Brief, encouraging feedback explaining what was right/wrong"
}}

Be fair — give partial credit for partially correct answers.
"""


class AdaptiveAssessmentService:

    # ─────────────────────────────
    # Mastery operations
    # ─────────────────────────────

    async def get_or_create_mastery(
        self,
        concept_id: int,
        student_id: str,
        db: AsyncSession
    ) -> Mastery:
        result = await db.execute(
            select(Mastery).where(
                Mastery.concept_id == concept_id,
                Mastery.student_id == student_id
            )
        )
        mastery = result.scalar_one_or_none()
        if mastery is None:
            mastery = Mastery(
                concept_id=concept_id,
                student_id=student_id,
                score=0.0,
                questions_seen=0,
                correct_answers=0
            )
            db.add(mastery)
            await db.flush()
        return mastery

    async def update_mastery(
        self,
        mastery: Mastery,
        is_correct: bool,
        difficulty: int,
        db: AsyncSession
    ) -> float:
        """
        Update mastery score using exponential weighted average.
        Difficulty multiplier rewards harder correct answers more.
        """
        difficulty_factor = {1: 0.6, 2: 1.0, 3: 1.5}.get(difficulty, 1.0)

        if is_correct:
            delta = MASTERY_CORRECT_WEIGHT * difficulty_factor
            mastery.score = min(1.0, mastery.score + delta)
            mastery.correct_answers += 1
        else:
            delta = MASTERY_WRONG_WEIGHT * difficulty_factor
            mastery.score = max(0.0, mastery.score - delta)

        mastery.questions_seen += 1
        mastery.last_updated = datetime.utcnow()

        # Save history point
        history = MasteryHistory(mastery_id=mastery.id, score=mastery.score)
        db.add(history)

        return mastery.score

    def select_next_difficulty(self, current_mastery: float, current_difficulty: int) -> int:
        """
        Adaptive difficulty selection.
        Goes up when mastery is high, down when struggling.
        """
        if current_mastery >= DIFFICULTY_UP_THRESHOLD and current_difficulty < 3:
            return min(3, current_difficulty + 1)
        elif current_mastery < DIFFICULTY_DOWN_THRESHOLD and current_difficulty > 1:
            return max(1, current_difficulty - 1)
        return current_difficulty

    def difficulty_label(self, d: int) -> str:
        return {1: "Easy", 2: "Medium", 3: "Hard"}.get(d, "Medium")

    # ─────────────────────────────
    # Question generation
    # ─────────────────────────────

    async def generate_question(
        self,
        concept: Concept,
        difficulty: int,
        question_type: str,
        db: AsyncSession,
        exclude_ids: Optional[List[int]] = None
    ) -> Optional[Question]:
        """
        Try DB first, then AI generation, then fallback.
        """
        # 1. Try existing questions in DB
        q_result = await db.execute(
            select(Question).where(
                Question.concept_id == concept.id,
                Question.difficulty == difficulty,
                Question.question_type == question_type
            )
        )
        existing = q_result.scalars().all()
        excluded = set(exclude_ids or [])
        available = [q for q in existing if q.id not in excluded]
        if available:
            return random.choice(available)

        # 2. Try AI generation
        try:
            return await self._ai_generate_question(concept, difficulty, question_type, db)
        except Exception as e:
            logger.warning(f"AI question generation failed: {e}")

        # 3. Fallback to static questions
        return self._fallback_question(concept, difficulty, question_type, db)

    async def _ai_generate_question(
        self,
        concept: Concept,
        difficulty: int,
        question_type: str,
        db: AsyncSession
    ) -> Question:
        """Generate a question using the LLM."""
        # Get context from RAG
        context_result = await rag_service.query(
            f"Explain {concept.name} with examples",
            db, n_chunks=3
        )
        context = context_result.get("response", "")[:800]

        difficulty_names = {1: "easy (basic recall)", 2: "medium (understanding)", 3: "hard (application/analysis)"}
        prompt_text = QUESTION_GEN_PROMPT.format(
            concept=concept.name,
            question_type=question_type,
            difficulty=difficulty_names.get(difficulty, "medium"),
            context=context
        )

        messages = [{"role": "user", "content": prompt_text}]
        raw = llm_provider.chat(messages)

        # Parse JSON from response
        data = self._parse_json_response(raw)

        # Save to DB
        q = Question(
            concept_id=concept.id,
            question_type=question_type,
            difficulty=difficulty,
            text=data.get("text", "Question unavailable"),
            options=data.get("options", []),
            correct_answer=data.get("correct_answer", ""),
            explanation=data.get("explanation", ""),
            is_demo=False
        )
        db.add(q)
        await db.flush()
        return q

    def _fallback_question(
        self,
        concept: Concept,
        difficulty: int,
        question_type: str,
        db: AsyncSession
    ) -> Question:
        """Static fallback questions for common concepts."""
        name = concept.name.lower()

        if "congestion" in name:
            q = Question(
                concept_id=concept.id,
                question_type="mcq",
                difficulty=difficulty,
                text="When TCP receives three duplicate ACKs, what action does it take?",
                options=[
                    "A) Wait for a timeout before retransmitting",
                    "B) Immediately retransmit the lost segment and set cwnd = ssthresh",
                    "C) Close the connection and reopen it",
                    "D) Double the congestion window"
                ],
                correct_answer="B) Immediately retransmit the lost segment and set cwnd = ssthresh",
                explanation=(
                    "Three duplicate ACKs trigger Fast Retransmit. "
                    "The sender immediately retransmits the missing segment and reduces cwnd to ssthresh, "
                    "then enters Fast Recovery rather than Slow Start."
                ),
                is_demo=True
            )
        elif "udp" in name:
            q = Question(
                concept_id=concept.id,
                question_type="mcq",
                difficulty=difficulty,
                text="Which of the following is NOT a characteristic of UDP?",
                options=[
                    "A) Connectionless communication",
                    "B) Guaranteed delivery of packets",
                    "C) Low overhead",
                    "D) No flow control"
                ],
                correct_answer="B) Guaranteed delivery of packets",
                explanation=(
                    "UDP does not guarantee packet delivery — "
                    "it provides no acknowledgements, retransmissions, or ordering guarantees. "
                    "This is a deliberate design for speed over reliability."
                ),
                is_demo=True
            )
        else:
            q = Question(
                concept_id=concept.id,
                question_type="mcq",
                difficulty=difficulty,
                text=f"Which statement best describes {concept.name}?",
                options=[
                    f"A) {concept.name} is a protocol for reliable data delivery",
                    f"B) {concept.name} operates at the network layer",
                    f"C) {concept.name} involves managing data flow between endpoints",
                    f"D) {concept.name} is primarily used for encryption"
                ],
                correct_answer=f"A) {concept.name} is a protocol for reliable data delivery",
                explanation=f"This question tests basic understanding of {concept.name}. Review your course materials for detailed information.",
                is_demo=True
            )

        # Don't persist transient fallback — return as unsaved object
        return q

    # ─────────────────────────────
    # Answer evaluation
    # ─────────────────────────────

    async def evaluate_answer(
        self,
        question: Question,
        student_answer: str
    ) -> Dict[str, Any]:
        """Evaluate a student's answer. Returns {is_correct, score, feedback}."""
        if question.question_type in ("mcq", "true_false"):
            # Exact / prefix match
            correct = question.correct_answer or ""
            is_correct = False
            if correct.strip():
                is_correct = (
                    student_answer.strip().lower() == correct.strip().lower()
                    or student_answer.strip().upper().startswith(correct.strip().upper()[0])
                    or correct.lower() in student_answer.lower()
                )
            return {
                "is_correct": is_correct,
                "score": 1.0 if is_correct else 0.0,
                "feedback": "Correct! Well done." if is_correct else f"Not quite. The correct answer is: {correct}"
            }
        else:
            # Short answer — use LLM evaluation
            try:
                prompt = EVAL_PROMPT.format(
                    question=question.text,
                    correct_answer=question.correct_answer or "",
                    student_answer=student_answer
                )
                messages = [{"role": "user", "content": prompt}]
                raw = llm_provider.chat(messages)
                data = self._parse_json_response(raw)
                return {
                    "is_correct": data.get("is_correct", False),
                    "score": data.get("score", 0.0),
                    "feedback": data.get("feedback", "")
                }
            except Exception as e:
                logger.warning(f"LLM eval failed: {e}. Using keyword match.")
                # Simple keyword fallback
                keywords = (question.correct_answer or "").lower().split()[:5]
                matches = sum(1 for kw in keywords if kw in student_answer.lower())
                score = matches / max(len(keywords), 1)
                is_correct = score >= 0.5
                return {
                    "is_correct": is_correct,
                    "score": score,
                    "feedback": "Partially correct. Review the explanation below." if is_correct else "Not quite right. Check the explanation."
                }

    def _parse_json_response(self, raw: str) -> Dict:
        """Extract JSON from LLM response (handles markdown code blocks)."""
        # Strip markdown
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*", "", raw)
        # Find first {...}
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {}


assessment_service = AdaptiveAssessmentService()
