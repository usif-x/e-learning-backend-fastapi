# app/routers/user_generated_question.py
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.user_generated_question import (
    AddMoreQuestionsRequest,
    AttemptResultResponse,
    GenerateUserQuestionsFromPDFRequest,
    GenerateUserQuestionsRequest,
    ParticipantListResponse,
    PendingAttemptsResponse,
    PublicQuestionListResponse,
    PublicQuestionSetResponse,
    QuestionDetail,
    QuestionWithResult,
    StartAttemptResponse,
    SubmitAttemptRequest,
    UserAttemptListResponse,
    UserGeneratedQuestionDetailResponse,
    UserGeneratedQuestionListResponse,
    UserGeneratedQuestionResponse,
)
from app.services.user_generated_question import UserGeneratedQuestionService

router = APIRouter(
    prefix="/user-questions",
    tags=["User Generated Questions"],
    responses={404: {"description": "Not found"}},
)


# ==================== Generate Questions ====================


@router.post(
    "/generate", response_model=UserGeneratedQuestionDetailResponse, status_code=201
)
async def generate_questions_from_topic(
    request: GenerateUserQuestionsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate questions from a topic using AI.
    Questions are saved and can be shared publicly or kept private.
    """
    service = UserGeneratedQuestionService(db)

    question_set = await service.generate_questions_from_topic(
        user_id=current_user.id,
        topic=request.topic,
        title=request.title,
        description=request.description,
        difficulty=request.difficulty,
        question_type=request.question_type,
        count=request.count,
        is_public=request.is_public,
        notes=request.notes,
    )

    return {
        "id": question_set.id,
        "user_id": question_set.user_id,
        "title": question_set.title,
        "description": question_set.description,
        "topic": question_set.topic,
        "difficulty": question_set.difficulty,
        "question_type": question_set.question_type,
        "is_public": question_set.is_public,
        "total_questions": question_set.total_questions,
        "source_type": question_set.source_type,
        "source_file_name": question_set.source_file_name,
        "attempt_count": question_set.attempt_count,
        "created_at": question_set.created_at,
        "updated_at": question_set.updated_at,
        "questions": question_set.questions,
        "creator_name": current_user.display_name,
    }


@router.post(
    "/generate-from-pdf",
    response_model=UserGeneratedQuestionDetailResponse,
    status_code=201,
)
async def generate_questions_from_pdf(
    file: UploadFile = File(..., description="PDF file to generate questions from"),
    title: str = Form(..., min_length=3, max_length=255),
    description: Optional[str] = Form(None),
    difficulty: str = Form("medium"),
    question_type: str = Form("multiple_choice"),
    count: int = Form(5, ge=1, le=50),
    is_public: bool = Form(False),
    notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate questions from a PDF file using AI.
    Upload a PDF and AI will extract content and generate questions.
    """
    service = UserGeneratedQuestionService(db)

    question_set = await service.generate_questions_from_pdf(
        user_id=current_user.id,
        file=file,
        title=title,
        description=description,
        difficulty=difficulty,
        question_type=question_type,
        count=count,
        is_public=is_public,
        notes=notes,
    )

    return {
        "id": question_set.id,
        "user_id": question_set.user_id,
        "title": question_set.title,
        "description": question_set.description,
        "topic": question_set.topic,
        "difficulty": question_set.difficulty,
        "question_type": question_set.question_type,
        "is_public": question_set.is_public,
        "total_questions": question_set.total_questions,
        "source_type": question_set.source_type,
        "source_file_name": question_set.source_file_name,
        "attempt_count": question_set.attempt_count,
        "created_at": question_set.created_at,
        "updated_at": question_set.updated_at,
        "questions": question_set.questions,
        "creator_name": current_user.display_name,
    }


@router.post(
    "/{question_set_id}/add-questions",
    response_model=UserGeneratedQuestionDetailResponse,
)
async def add_more_questions(
    question_set_id: int,
    request: AddMoreQuestionsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add more questions to an existing question set.
    AI will automatically avoid duplicating previous questions.
    """
    service = UserGeneratedQuestionService(db)

    question_set = await service.add_more_questions(
        question_set_id=question_set_id,
        user_id=current_user.id,
        count=request.count,
        notes=request.notes,
    )

    return {
        "id": question_set.id,
        "user_id": question_set.user_id,
        "title": question_set.title,
        "description": question_set.description,
        "topic": question_set.topic,
        "difficulty": question_set.difficulty,
        "question_type": question_set.question_type,
        "is_public": question_set.is_public,
        "total_questions": question_set.total_questions,
        "source_type": question_set.source_type,
        "source_file_name": question_set.source_file_name,
        "attempt_count": question_set.attempt_count,
        "created_at": question_set.created_at,
        "updated_at": question_set.updated_at,
        "questions": question_set.questions,
        "creator_name": current_user.display_name,
    }


# ==================== Manage My Questions ====================


@router.get("/my", response_model=UserGeneratedQuestionListResponse)
def get_my_question_sets(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all question sets created by current user.
    """
    service = UserGeneratedQuestionService(db)
    question_sets, pagination = service.get_user_question_sets(
        user_id=current_user.id,
        page=page,
        size=size,
    )

    return {
        "question_sets": [
            {
                "id": qs.id,
                "user_id": qs.user_id,
                "title": qs.title,
                "description": qs.description,
                "topic": qs.topic,
                "difficulty": qs.difficulty,
                "question_type": qs.question_type,
                "is_public": qs.is_public,
                "total_questions": qs.total_questions,
                "source_type": qs.source_type,
                "source_file_name": qs.source_file_name,
                "attempt_count": qs.attempt_count,
                "created_at": qs.created_at,
                "updated_at": qs.updated_at,
                "creator_name": current_user.display_name,
            }
            for qs in question_sets
        ],
        **pagination,
    }


@router.get("/my/{question_set_id}", response_model=UserGeneratedQuestionDetailResponse)
def get_my_question_set_detail(
    question_set_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed view of a question set (with all questions and answers).
    Only the creator can see full details.
    """
    service = UserGeneratedQuestionService(db)
    question_set = service.get_question_set_detail(
        question_set_id=question_set_id,
        user_id=current_user.id,
    )

    return {
        "id": question_set.id,
        "user_id": question_set.user_id,
        "title": question_set.title,
        "description": question_set.description,
        "topic": question_set.topic,
        "difficulty": question_set.difficulty,
        "question_type": question_set.question_type,
        "is_public": question_set.is_public,
        "total_questions": question_set.total_questions,
        "source_type": question_set.source_type,
        "source_file_name": question_set.source_file_name,
        "attempt_count": question_set.attempt_count,
        "created_at": question_set.created_at,
        "updated_at": question_set.updated_at,
        "questions": question_set.questions,
        "creator_name": current_user.display_name,
    }


@router.patch("/my/{question_set_id}", response_model=UserGeneratedQuestionResponse)
def update_my_question_set(
    question_set_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    is_public: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update question set metadata (title, description, privacy).
    Cannot modify questions after creation (use add-questions instead).
    """
    service = UserGeneratedQuestionService(db)
    question_set = service.update_question_set(
        question_set_id=question_set_id,
        user_id=current_user.id,
        title=title,
        description=description,
        is_public=is_public,
    )

    return {
        "id": question_set.id,
        "user_id": question_set.user_id,
        "title": question_set.title,
        "description": question_set.description,
        "topic": question_set.topic,
        "difficulty": question_set.difficulty,
        "question_type": question_set.question_type,
        "is_public": question_set.is_public,
        "total_questions": question_set.total_questions,
        "source_type": question_set.source_type,
        "source_file_name": question_set.source_file_name,
        "attempt_count": question_set.attempt_count,
        "created_at": question_set.created_at,
        "updated_at": question_set.updated_at,
        "creator_name": current_user.display_name,
    }


@router.delete("/my/{question_set_id}", status_code=204)
def delete_my_question_set(
    question_set_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a question set.
    Only the creator can delete their question sets.
    """
    service = UserGeneratedQuestionService(db)
    service.delete_question_set(
        question_set_id=question_set_id,
        user_id=current_user.id,
    )
    return None


# ==================== Public Questions (Discovery) ====================


@router.get("/public", response_model=PublicQuestionListResponse)
def get_public_question_sets(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    difficulty: Optional[str] = Query(None, pattern="^(easy|medium|hard)$"),
    search: Optional[str] = Query(None, max_length=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Browse all public question sets created by other users.
    Shows if you've attempted each set and your best score.
    """
    service = UserGeneratedQuestionService(db)
    results, pagination = service.get_public_question_sets(
        current_user_id=current_user.id,
        page=page,
        size=size,
        difficulty=difficulty,
        search=search,
    )

    return {
        "question_sets": [
            {
                "id": r["question_set"].id,
                "title": r["question_set"].title,
                "description": r["question_set"].description,
                "topic": r["question_set"].topic,
                "difficulty": r["question_set"].difficulty,
                "question_type": r["question_set"].question_type,
                "total_questions": r["question_set"].total_questions,
                "attempt_count": r["question_set"].attempt_count,
                "created_at": r["question_set"].created_at,
                "creator_name": r["creator_name"],
                "user_has_attempted": r["user_has_attempted"],
                "user_best_score": r["user_best_score"],
                "user_has_pending_attempt": r["user_has_pending_attempt"],
                "pending_attempt_id": r["pending_attempt_id"],
                "pending_attempt_started_at": r["pending_attempt_started_at"],
            }
            for r in results
        ],
        **pagination,
    }


@router.get("/{question_set_id}/participants", response_model=ParticipantListResponse)
def get_question_set_participants(
    question_set_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all users who attempted this question set with their scores.
    Shows leaderboard ranked by best score with pagination.
    Only works for public question sets.
    """
    service = UserGeneratedQuestionService(db)
    result = service.get_question_set_participants(
        question_set_id=question_set_id,
        page=page,
        size=size,
    )

    return result


@router.get("/attempts/pending", response_model=PendingAttemptsResponse)
def get_pending_attempts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all pending (incomplete) attempts for current user.
    Useful to show which question sets the user started but didn't complete.
    """
    service = UserGeneratedQuestionService(db)
    pending_attempts = service.get_user_pending_attempts(user_id=current_user.id)

    pending_list = []
    for attempt in pending_attempts:
        question_set = attempt.question_set
        pending_list.append(
            {
                "attempt_id": attempt.id,
                "question_set_id": question_set.id,
                "question_set_title": question_set.title,
                "question_set_topic": question_set.topic,
                "difficulty": question_set.difficulty,
                "total_questions": attempt.total_questions,
                "started_at": attempt.started_at,
            }
        )

    return {
        "pending_attempts": pending_list,
        "total": len(pending_list),
    }


# ==================== Attempt Questions ====================


@router.post("/{question_set_id}/attempt", response_model=StartAttemptResponse)
def start_question_attempt(
    question_set_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Start or resume an attempt on a question set (public or your own).
    If you have an incomplete attempt, it will be resumed automatically.
    Returns questions without correct answers.
    """
    service = UserGeneratedQuestionService(db)
    attempt, question_set = service.start_attempt(
        question_set_id=question_set_id,
        user_id=current_user.id,
    )

    # Build questions without correct answers
    questions_for_attempt = []
    for idx, q in enumerate(question_set.questions):
        questions_for_attempt.append(
            {
                "question": q.get("question"),
                "options": q.get("options", []),
                "question_type": q.get("question_type", "multiple_choice"),
            }
        )

    return {
        "attempt_id": attempt.id,
        "question_set_id": question_set.id,
        "title": question_set.title,
        "description": question_set.description,
        "topic": question_set.topic,
        "difficulty": question_set.difficulty,
        "total_questions": question_set.total_questions,
        "questions": questions_for_attempt,
        "started_at": attempt.started_at,
    }


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptResultResponse)
def submit_question_attempt(
    attempt_id: int,
    request: SubmitAttemptRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submit answers for an attempt.
    Returns detailed results with correct answers and explanations.
    """
    service = UserGeneratedQuestionService(db)
    attempt = service.submit_attempt(
        attempt_id=attempt_id,
        user_id=current_user.id,
        answers=request.answers,
        time_taken=request.time_taken,
    )

    question_set = attempt.question_set

    # Build questions with results
    questions_with_results = []
    if attempt.answers:
        answer_map = {ans["question_index"]: ans for ans in attempt.answers}

        for idx, question in enumerate(question_set.questions):
            answer_data = answer_map.get(idx, {})

            questions_with_results.append(
                {
                    "question": question.get("question"),
                    "options": question.get("options", []),
                    "user_answer": answer_data.get("selected_answer"),
                    "correct_answer": question.get("correct_answer"),
                    "is_correct": answer_data.get("is_correct", False),
                    "explanation_en": question.get("explanation_en"),
                    "explanation_ar": question.get("explanation_ar"),
                }
            )

    return {
        "id": attempt.id,
        "question_set_id": attempt.question_set_id,
        "user_id": attempt.user_id,
        "score": attempt.score,
        "correct_answers": attempt.correct_answers,
        "total_questions": attempt.total_questions,
        "time_taken": attempt.time_taken,
        "is_completed": attempt.is_completed,
        "started_at": attempt.started_at,
        "completed_at": attempt.completed_at,
        "title": question_set.title,
        "topic": question_set.topic,
        "difficulty": question_set.difficulty,
        "questions_with_results": questions_with_results,
    }


@router.get("/attempts/my", response_model=UserAttemptListResponse)
def get_my_attempts(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all attempts made by current user on any question sets.
    """
    service = UserGeneratedQuestionService(db)
    attempts, pagination = service.get_user_attempts(
        user_id=current_user.id,
        page=page,
        size=size,
    )

    return {
        "attempts": [
            {
                "id": att.id,
                "question_set_id": att.question_set_id,
                "user_id": att.user_id,
                "score": att.score,
                "correct_answers": att.correct_answers,
                "total_questions": att.total_questions,
                "time_taken": att.time_taken,
                "is_completed": att.is_completed,
                "started_at": att.started_at,
                "completed_at": att.completed_at,
                "title": att.question_set.title,
                "topic": att.question_set.topic,
                "difficulty": att.question_set.difficulty,
                "questions_with_results": None,  # Not included in list view
            }
            for att in attempts
        ],
        **pagination,
    }


@router.get("/attempts/{attempt_id}", response_model=AttemptResultResponse)
def get_attempt_detail(
    attempt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed result of a specific attempt with all questions and answers.
    """
    service = UserGeneratedQuestionService(db)
    attempt = service.get_attempt_detail(
        attempt_id=attempt_id,
        user_id=current_user.id,
    )

    question_set = attempt.question_set

    # Build questions with results
    questions_with_results = []
    if attempt.answers:
        answer_map = {ans["question_index"]: ans for ans in attempt.answers}

        for idx, question in enumerate(question_set.questions):
            answer_data = answer_map.get(idx, {})

            questions_with_results.append(
                {
                    "question": question.get("question"),
                    "options": question.get("options", []),
                    "user_answer": answer_data.get("selected_answer"),
                    "correct_answer": question.get("correct_answer"),
                    "is_correct": answer_data.get("is_correct", False),
                    "explanation_en": question.get("explanation_en"),
                    "explanation_ar": question.get("explanation_ar"),
                }
            )

    return {
        "id": attempt.id,
        "question_set_id": attempt.question_set_id,
        "user_id": attempt.user_id,
        "score": attempt.score,
        "correct_answers": attempt.correct_answers,
        "total_questions": attempt.total_questions,
        "time_taken": attempt.time_taken,
        "is_completed": attempt.is_completed,
        "started_at": attempt.started_at,
        "completed_at": attempt.completed_at,
        "title": question_set.title,
        "topic": question_set.topic,
        "difficulty": question_set.difficulty,
        "questions_with_results": questions_with_results,
    }
