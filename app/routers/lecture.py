# app/routers/lecture.py
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin, get_current_user
from app.models.admin import Admin
from app.models.quiz_attempt import QuizAttempt
from app.models.user import User
from app.schemas.lecture import (
    GenerateQuizRequest,
    GenerateQuizResponse,
    LectureContentCreate,
    LectureContentListResponse,
    LectureContentResponse,
    LectureContentUpdate,
    LectureCreate,
    LectureListResponse,
    LectureResponse,
    LectureUpdate,
    QuizAttemptCreate,
    QuizAttemptListResponse,
    QuizAttemptResponse,
    QuizAttemptStats,
    StartQuizResponse,
)
from app.services.lecture import LectureService
from app.services.quiz_attempt import QuizAttemptService
from app.utils.ai import ai_service

router = APIRouter(
    prefix="/courses/{course_id}/lectures",
    tags=["Lectures"],
    responses={404: {"description": "Not found"}},
)


# ==================== Lecture Endpoints ====================


@router.post("/", response_model=LectureResponse, status_code=201)
def create_lecture(
    course_id: int,
    lecture_in: LectureCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Create a new lecture in a course.
    Admin only.
    """
    service = LectureService(db)
    return service.create_lecture(course_id, lecture_in)


@router.get("/", response_model=LectureListResponse)
def list_lectures(
    course_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Get all lectures for a course.
    Returns lectures ordered by position.
    """
    service = LectureService(db)
    lectures, pagination = service.get_lectures(course_id, page, size)
    return {"lectures": lectures, **pagination}


@router.get("/{lecture_id}", response_model=LectureResponse)
def get_lecture(
    course_id: int,
    lecture_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific lecture by ID"""
    service = LectureService(db)
    lecture = service.get_lecture(lecture_id, course_id)

    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lecture not found",
        )

    return lecture


@router.patch("/{lecture_id}", response_model=LectureResponse)
def update_lecture(
    course_id: int,
    lecture_id: int,
    lecture_in: LectureUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Update a lecture.
    Admin only.
    """
    service = LectureService(db)
    lecture = service.update_lecture(lecture_id, lecture_in, course_id)

    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lecture not found",
        )

    return lecture


@router.delete("/{lecture_id}", status_code=204)
def delete_lecture(
    course_id: int,
    lecture_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Delete a lecture.
    Admin only.
    """
    service = LectureService(db)
    service.delete_lecture(lecture_id, course_id)
    return None


# ==================== Lecture Content Endpoints ====================


@router.post(
    "/{lecture_id}/contents", response_model=LectureContentResponse, status_code=201
)
def create_content(
    course_id: int,
    lecture_id: int,
    content_in: LectureContentCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Create content for a lecture.
    Content types: video, photo, file, audio, link, quiz.
    For quiz type, provide questions array. For others, provide source.
    Admin only.
    """
    service = LectureService(db)
    return service.create_content(lecture_id, course_id, content_in)


@router.get("/{lecture_id}/contents", response_model=LectureContentListResponse)
def list_contents(
    course_id: int,
    lecture_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    content_type: Optional[str] = Query(
        None, pattern="^(video|photo|file|audio|link|quiz)$"
    ),
    db: Session = Depends(get_db),
):
    """
    Get all contents for a lecture.
    Optionally filter by content_type.
    Returns contents ordered by position.
    """
    service = LectureService(db)
    contents, pagination = service.get_contents(
        lecture_id, course_id, page, size, content_type
    )
    return {"contents": contents, **pagination}


@router.get(
    "/{lecture_id}/contents/{content_id}", response_model=LectureContentResponse
)
def get_content(
    course_id: int,
    lecture_id: int,
    content_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific content item by ID"""
    service = LectureService(db)
    content = service.get_content(content_id)

    if (
        not content
        or content.lecture_id != lecture_id
        or content.course_id != course_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    return content


@router.patch(
    "/{lecture_id}/contents/{content_id}", response_model=LectureContentResponse
)
def update_content(
    course_id: int,
    lecture_id: int,
    content_id: int,
    content_in: LectureContentUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Update a content item.
    Admin only.
    """
    service = LectureService(db)
    content = service.update_content(content_id, content_in)

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found",
        )

    return content


@router.delete("/{lecture_id}/contents/{content_id}", status_code=204)
def delete_content(
    course_id: int,
    lecture_id: int,
    content_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Delete a content item.
    Admin only.
    """
    service = LectureService(db)
    service.delete_content(content_id)
    return None


# ==================== Quiz Attempt Endpoints ====================


@router.post(
    "/{lecture_id}/contents/{content_id}/start-quiz",
    response_model=StartQuizResponse,
)
def start_quiz_attempt(
    course_id: int,
    lecture_id: int,
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start a quiz attempt and get questions.
    This is the ONLY endpoint that returns quiz questions.
    Validates attempt limits before returning questions.
    """
    from sqlalchemy import and_

    from app.models.lecture_content import LectureContent
    from app.models.quiz_attempt import QuizAttempt

    # Get quiz content
    content = (
        db.query(LectureContent)
        .filter(
            and_(
                LectureContent.id == content_id,
                LectureContent.course_id == course_id,
                LectureContent.lecture_id == lecture_id,
                LectureContent.content_type == "quiz",
            )
        )
        .first()
    )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        )

    # Check attempts (only count completed attempts for max_attempts validation)
    attempts_count = (
        db.query(QuizAttempt)
        .filter(
            and_(
                QuizAttempt.content_id == content_id,
                QuizAttempt.user_id == current_user.id,
                QuizAttempt.is_completed == 1,
            )
        )
        .count()
    )

    can_attempt = True
    attempts_remaining = None
    message = None

    if content.max_attempts:
        attempts_remaining = content.max_attempts - attempts_count
        if attempts_remaining <= 0:
            can_attempt = False
            message = f"Maximum attempts ({content.max_attempts}) reached"

    if not can_attempt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    # Expire all to ensure we get fresh data from database
    db.expire_all()

    # Check for existing incomplete attempt
    incomplete_attempt = (
        db.query(QuizAttempt)
        .filter(
            and_(
                QuizAttempt.content_id == content_id,
                QuizAttempt.user_id == current_user.id,
                QuizAttempt.is_completed == 0,
            )
        )
        .first()
    )

    # Create new attempt record if no incomplete attempt exists
    if not incomplete_attempt:
        try:
            new_attempt = QuizAttempt(
                user_id=current_user.id,
                content_id=content_id,
                course_id=course_id,
                lecture_id=lecture_id,
                total_questions=len(content.questions) if content.questions else 0,
                is_completed=0,
                started_at=datetime.utcnow(),
            )
            db.add(new_attempt)
            db.commit()
            db.refresh(new_attempt)
            attempt_id = new_attempt.id
        except Exception:
            # If commit failed (e.g., concurrent request), rollback and re-query
            db.rollback()
            incomplete_attempt = (
                db.query(QuizAttempt)
                .filter(
                    and_(
                        QuizAttempt.content_id == content_id,
                        QuizAttempt.user_id == current_user.id,
                        QuizAttempt.is_completed == 0,
                    )
                )
                .first()
            )
            if incomplete_attempt:
                attempt_id = incomplete_attempt.id
            else:
                raise
    else:
        attempt_id = incomplete_attempt.id

    # Strip correct answers and explanations from questions for security
    questions_for_attempt = []
    if content.questions:
        for question in content.questions:
            questions_for_attempt.append(
                {
                    "question": question["question"],
                    "options": question["options"],
                }
            )

    # Build response with sanitized questions
    content_response = {
        "id": content.id,
        "course_id": content.course_id,
        "lecture_id": content.lecture_id,
        "content_type": content.content_type,
        "source": content.source,
        "questions": questions_for_attempt,
        "quiz_duration": content.quiz_duration,
        "max_attempts": content.max_attempts,
        "passing_score": content.passing_score,
        "show_correct_answers": content.show_correct_answers,
        "randomize_questions": content.randomize_questions,
        "randomize_options": content.randomize_options,
        "title": content.title,
        "description": content.description,
        "position": content.position,
        "created_at": content.created_at,
        "updated_at": content.updated_at,
    }

    return {
        "content": content_response,
        "attempt_id": attempt_id,
        "attempts_used": attempts_count,
        "attempts_remaining": attempts_remaining,
        "can_attempt": can_attempt,
        "message": (
            "Quiz started successfully"
            if not incomplete_attempt
            else "Resuming incomplete attempt"
        ),
    }


@router.get(
    "/{lecture_id}/contents/{content_id}/resume-quiz",
    response_model=StartQuizResponse,
)
def resume_quiz_attempt(
    course_id: int,
    lecture_id: int,
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get incomplete quiz attempt to resume.
    Returns the quiz questions without correct answers.
    If no incomplete attempt exists, returns 404.
    """
    from sqlalchemy import and_

    from app.models.lecture_content import LectureContent
    from app.models.quiz_attempt import QuizAttempt

    # Get incomplete attempt
    incomplete_attempt = (
        db.query(QuizAttempt)
        .filter(
            and_(
                QuizAttempt.content_id == content_id,
                QuizAttempt.user_id == current_user.id,
                QuizAttempt.is_completed == 0,
            )
        )
        .first()
    )

    if not incomplete_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No incomplete attempt found. Start a new quiz attempt.",
        )

    # Get quiz content
    content = (
        db.query(LectureContent)
        .filter(
            and_(
                LectureContent.id == content_id,
                LectureContent.course_id == course_id,
                LectureContent.lecture_id == lecture_id,
                LectureContent.content_type == "quiz",
            )
        )
        .first()
    )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found",
        )

    # Count completed attempts only (for max_attempts calculation)
    attempts_count = (
        db.query(QuizAttempt)
        .filter(
            and_(
                QuizAttempt.content_id == content_id,
                QuizAttempt.user_id == current_user.id,
                QuizAttempt.is_completed == 1,
            )
        )
        .count()
    )

    attempts_remaining = None
    if content.max_attempts:
        attempts_remaining = content.max_attempts - attempts_count

    # Strip correct answers and explanations from questions
    questions_for_attempt = []
    if content.questions:
        for question in content.questions:
            questions_for_attempt.append(
                {
                    "question": question["question"],
                    "options": question["options"],
                }
            )

    # Build response
    content_response = {
        "id": content.id,
        "course_id": content.course_id,
        "lecture_id": content.lecture_id,
        "content_type": content.content_type,
        "source": content.source,
        "questions": questions_for_attempt,
        "quiz_duration": content.quiz_duration,
        "max_attempts": content.max_attempts,
        "passing_score": content.passing_score,
        "show_correct_answers": content.show_correct_answers,
        "randomize_questions": content.randomize_questions,
        "randomize_options": content.randomize_options,
        "title": content.title,
        "description": content.description,
        "position": content.position,
        "created_at": content.created_at,
        "updated_at": content.updated_at,
    }

    return {
        "content": content_response,
        "attempt_id": incomplete_attempt.id,
        "attempts_used": attempts_count,
        "attempts_remaining": attempts_remaining,
        "can_attempt": True,
        "message": "Resuming incomplete attempt",
    }


@router.post(
    "/{lecture_id}/contents/{content_id}/attempts",
    response_model=QuizAttemptResponse,
    status_code=201,
)
def submit_quiz_attempt(
    course_id: int,
    lecture_id: int,
    content_id: int,
    attempt_in: QuizAttemptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a quiz attempt.
    Can complete an existing incomplete attempt by providing attempt_id,
    or create a new completed attempt.
    Validates answers, calculates score, and returns results.
    Shows correct answers based on quiz settings.
    """
    from sqlalchemy import and_

    from app.models.lecture_content import LectureContent

    service = QuizAttemptService(db)
    quiz_attempt = service.submit_attempt(
        content_id,
        course_id,
        lecture_id,
        current_user.id,
        attempt_in,
        attempt_id=attempt_in.attempt_id,
    )

    # Expire all objects to ensure fresh state from database
    db.expire_all()

    # Get quiz content for settings and questions
    content = (
        db.query(LectureContent)
        .filter(
            and_(
                LectureContent.id == content_id,
                LectureContent.content_type == "quiz",
            )
        )
        .first()
    )

    # Build detailed results if show_correct_answers is enabled
    questions_with_results = None
    if content and content.show_correct_answers and content.questions:
        questions_with_results = []

        for answer_data in quiz_attempt.answers:
            question_idx = answer_data["question_index"]
            user_answer = answer_data["selected_answer"]
            is_correct = answer_data["is_correct"]

            question = content.questions[question_idx]

            result = {
                "question": question["question"],
                "options": question["options"],
                "user_answer": user_answer,
                "correct_answer": question["correct_answer"],
                "is_correct": is_correct,
                "explanation_en": question.get("explanation_en"),
                "explanation_ar": question.get("explanation_ar"),
            }
            questions_with_results.append(result)

    # Build response
    response = {
        "id": quiz_attempt.id,
        "user_id": quiz_attempt.user_id,
        "content_id": quiz_attempt.content_id,
        "course_id": quiz_attempt.course_id,
        "lecture_id": quiz_attempt.lecture_id,
        "score": float(quiz_attempt.score) if quiz_attempt.score else None,
        "total_questions": quiz_attempt.total_questions,
        "correct_answers": quiz_attempt.correct_answers,
        "time_taken": quiz_attempt.time_taken,
        "started_at": quiz_attempt.started_at,
        "completed_at": quiz_attempt.completed_at,
        "created_at": quiz_attempt.created_at,
        "is_completed": quiz_attempt.is_completed,
        "questions_with_results": questions_with_results,
        "show_correct_answers": bool(content.show_correct_answers) if content else True,
    }

    return response


@router.get(
    "/{lecture_id}/contents/{content_id}/attempts",
    response_model=QuizAttemptListResponse,
)
def get_quiz_attempts(
    course_id: int,
    lecture_id: int,
    content_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get user's quiz attempts for a specific quiz.
    Returns incomplete attempt (if exists) and completed attempts.
    Completed attempts are ordered by completion date (newest first).
    """
    service = QuizAttemptService(db)
    incomplete_attempt, completed_attempts, pagination = service.get_user_attempts(
        content_id, current_user.id, page, size
    )
    return {
        "incomplete_attempt": incomplete_attempt,
        "completed_attempts": completed_attempts,
        **pagination,
    }


@router.get(
    "/{lecture_id}/contents/{content_id}/stats",
    response_model=QuizAttemptStats,
)
def get_quiz_stats(
    course_id: int,
    lecture_id: int,
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get statistics for a user's quiz attempts.
    Includes total attempts, best score, average score, and pass status.
    """
    service = QuizAttemptService(db)
    return service.get_attempt_stats(content_id, current_user.id)


# ==================== AI Quiz Generation Endpoints ====================


@router.post("/ai/generate-quiz", response_model=GenerateQuizResponse)
async def generate_quiz_questions(
    course_id: int,
    request: GenerateQuizRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Generate quiz questions using AI based on a topic.
    Admin only.

    Returns AI-generated questions for review and editing before saving.
    Frontend can modify/delete questions and then submit to create content endpoint.
    """
    if not ai_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured",
        )

    # Verify lecture exists and belongs to the course
    service = LectureService(db)
    lecture = service.get_lecture(request.lecture_id, course_id)
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lecture not found in this course",
        )

    try:
        # Generate questions using AI
        result = await ai_service.generate_questions(
            topic=request.topic,
            difficulty=request.difficulty,
            count=request.count,
            question_type="multiple_choice",
        )

        # Parse questions from AI response
        questions = result.get("questions", [])

        if not questions:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI failed to generate questions",
            )

        return {
            "success": True,
            "topic": request.topic,
            "questions": questions,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate questions: {str(e)}",
        )


@router.post("/ai/generate-quiz-from-pdf", response_model=GenerateQuizResponse)
async def generate_quiz_from_pdf(
    course_id: int,
    lecture_id: int = Query(..., description="Lecture ID to associate quiz with"),
    file: UploadFile = File(..., description="PDF file to generate questions from"),
    difficulty: str = Query("medium", pattern="^(easy|medium|hard)$"),
    count: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Generate quiz questions from a PDF file using AI.
    Admin only.

    Upload a PDF and AI will extract content and generate relevant questions.
    Returns questions for review and editing before saving.
    """
    if not ai_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured",
        )

    # Verify lecture exists and belongs to the course
    service = LectureService(db)
    lecture = service.get_lecture(lecture_id, course_id)
    if not lecture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lecture not found in this course",
        )

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF",
        )

    try:
        # Generate questions from PDF using AI
        result = await ai_service.generate_questions_from_pdf(
            file=file,
            difficulty=difficulty,
            count=count,
            question_type="multiple_choice",
        )

        # Parse questions from AI response
        questions = result.get("questions", [])

        if not questions:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI failed to generate questions from PDF",
            )

        # Extract topic from filename (remove .pdf extension)
        topic = file.filename.rsplit(".", 1)[0] if file.filename else "PDF Content"

        return {
            "success": True,
            "topic": topic,
            "questions": questions,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate questions from PDF: {str(e)}",
        )
