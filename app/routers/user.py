# app/routers/users.py

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from httpx import get
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User

# Import the specific schemas we need
from app.schemas.lecture import UserAllQuizzesAnalytics, UserQuizAnalytics
from app.schemas.user import UserResponse
from app.services.user import UserService

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a single user by their ID.
    """
    service = UserService(db)
    db_user = service.get_user(user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.post("/{user_id}/charge-wallet")
def charge_user_wallet(user_id: int, amount: float, db: Session = Depends(get_db)):
    """
    Charge (add funds to) a user's wallet.
    """
    service = UserService(db)
    success = service.add_funds_to_wallet(user_id=user_id, amount=amount)
    if not success:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    return {"message": "Wallet charged successfully"}


@router.get("/me/quiz-analytics", response_model=UserAllQuizzesAnalytics)
def get_my_quiz_analytics(
    course_id: Optional[int] = Query(None, description="Filter by course ID"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current user's quiz analytics.
    Returns all completed quiz attempts with detailed results.
    Correct answers are shown based on each quiz's show_correct_answers setting.
    """
    import math

    from sqlalchemy import and_

    from app.models.lecture_content import LectureContent
    from app.models.quiz_attempt import QuizAttempt

    # Query completed attempts
    query = db.query(QuizAttempt).filter(
        and_(
            QuizAttempt.user_id == current_user.id,
            QuizAttempt.is_completed == 1,
        )
    )

    if course_id:
        query = query.filter(QuizAttempt.course_id == course_id)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * size
    attempts = (
        query.order_by(QuizAttempt.completed_at.desc()).offset(offset).limit(size).all()
    )

    # Build analytics for each attempt
    analytics_list = []
    for attempt in attempts:
        # Get quiz content for title
        content = (
            db.query(LectureContent)
            .filter(LectureContent.id == attempt.content_id)
            .first()
        )

        # Don't include question details in list view
        analytics_list.append(
            {
                "content_id": attempt.content_id,
                "quiz_title": content.title if content else None,
                "course_id": attempt.course_id,
                "lecture_id": attempt.lecture_id,
                "attempt_id": attempt.id,
                "score": attempt.score,
                "total_questions": attempt.total_questions,
                "correct_answers": attempt.correct_answers,
                "time_taken": attempt.time_taken,
                "started_at": attempt.started_at,
                "completed_at": attempt.completed_at,
                "is_completed": attempt.is_completed,
                "questions_with_results": None,  # Don't send questions in list view
            }
        )

    # Pagination metadata
    total_pages = math.ceil(total / size) if size > 0 else 0

    return {
        "quizzes": analytics_list,
        "total": total,
        "page": page,
        "size": size,
        "total_pages": total_pages,
    }


@router.get(
    "/me/quiz-analytics/{attempt_id}",
    response_model=UserQuizAnalytics,
)
def get_my_quiz_attempt_details(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed analytics for a specific quiz attempt.
    Correct answers are shown based on the quiz's show_correct_answers setting.
    """
    from app.models.lecture_content import LectureContent
    from app.models.quiz_attempt import QuizAttempt

    # Get the attempt
    attempt = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.id == attempt_id,
            QuizAttempt.user_id == current_user.id,
            QuizAttempt.is_completed == 1,
        )
        .first()
    )

    if not attempt:
        raise HTTPException(
            status_code=404,
            detail="Quiz attempt not found or not completed",
        )

    # Get quiz content for title and settings
    content = (
        db.query(LectureContent).filter(LectureContent.id == attempt.content_id).first()
    )

    questions_with_results = None

    # Only show correct answers if quiz setting allows it
    if (
        content
        and content.show_correct_answers
        and content.questions
        and attempt.answers
    ):
        questions_with_results = []

        for answer_data in attempt.answers:
            question_idx = answer_data["question_index"]
            user_answer = answer_data["selected_answer"]
            correct_answer = answer_data["correct_answer"]
            is_correct = answer_data["is_correct"]

            question = content.questions[question_idx]

            result = {
                "question": question["question"],
                "options": question["options"],
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "explanation_en": question.get("explanation_en"),
                "explanation_ar": question.get("explanation_ar"),
            }

            questions_with_results.append(result)

    return {
        "content_id": attempt.content_id,
        "quiz_title": content.title if content else None,
        "course_id": attempt.course_id,
        "lecture_id": attempt.lecture_id,
        "attempt_id": attempt.id,
        "score": attempt.score,
        "total_questions": attempt.total_questions,
        "correct_answers": attempt.correct_answers,
        "time_taken": attempt.time_taken,
        "started_at": attempt.started_at,
        "completed_at": attempt.completed_at,
        "is_completed": attempt.is_completed,
        "questions_with_results": questions_with_results,
    }
