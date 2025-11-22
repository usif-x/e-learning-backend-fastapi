# app/routers/quiz_source.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.models.admin import Admin
from app.schemas.quiz_source import QuizSourceListResponse, QuizSourceResponse
from app.services.quiz_source import QuizSourceService

router = APIRouter(
    prefix="/quiz-sources",
    tags=["Quiz Sources"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=QuizSourceListResponse)
def list_quiz_sources(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Get all quiz sources.
    Admin only.
    """
    service = QuizSourceService(db)
    sources, pagination = service.get_sources(page, size)
    return {"sources": sources, **pagination}


@router.get("/{source_id}", response_model=QuizSourceResponse)
def get_quiz_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """Get a specific quiz source by ID. Admin only."""
    service = QuizSourceService(db)
    source = service.get_source(source_id)
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz source not found",
        )
    return source


@router.delete("/{source_id}", status_code=204)
def delete_quiz_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Delete a quiz source.
    Admin only.
    """
    service = QuizSourceService(db)
    if not service.delete_source(source_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz source not found",
        )
    return None
