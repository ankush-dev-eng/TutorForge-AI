"""Learning Path routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from learning_path_service import learning_path_service

router = APIRouter()


@router.get("/")
async def get_learning_path(
    student_id: str = "default_student",
    db: AsyncSession = Depends(get_db)
):
    """Get (or generate) personalized learning path."""
    return await learning_path_service.generate(student_id, db)


@router.post("/regenerate")
async def regenerate_learning_path(
    student_id: str = "default_student",
    db: AsyncSession = Depends(get_db)
):
    """Force regeneration of learning path."""
    return await learning_path_service.generate(student_id, db)
