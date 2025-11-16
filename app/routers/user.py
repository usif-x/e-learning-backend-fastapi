# app/routers/users.py

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from httpx import get
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.course_enrollment import (
    CourseEnrollmentCreate,
    CourseEnrollmentResponse,
    EnrolledCourseResponse,
    EnrolledCoursesListResponse,
)

# Import the specific schemas we need
from app.schemas.lecture import (
    PracticeQuizDetailedResultResponse,
    PracticeQuizRequest,
    PracticeQuizResultsListResponse,
    StartQuizResponse,
    UserAllQuizzesAnalytics,
    UserQuizAnalytics,
)
from app.schemas.user import UpdatePasswordRequest, UserProfileResponse, UserResponse
from app.services.course_enrollment import CourseEnrollmentService
from app.services.practice_quiz import PracticeQuizService
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


@router.get("/me", response_model=UserProfileResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user's detailed profile information.
    """
    return current_user


@router.put("/me/password")
def update_password(
    request: UpdatePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update current user's password.
    Requires current password verification.
    """
    # Validate new password confirmation
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=400, detail="New password and confirmation do not match"
        )

    # Validate password length
    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=400, detail="Password must be at least 6 characters long"
        )

    service = UserService(db)
    success = service.update_password(
        user_id=current_user.id,
        current_password=request.current_password,
        new_password=request.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect or user has no password set",
        )

    return {"message": "Password updated successfully"}


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


@router.post("/me/practice-quiz/generate")
def generate_practice_quiz(
    request: PracticeQuizRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a practice quiz from user's incorrect/unanswered questions, specific lectures, or specific quizzes.
    This is user-specific and NOT added to course content.
    Returns the practice quiz ID for later retrieval.

    Modes:
    - quiz_ids: Generate from specific quiz content IDs (requires course_id)
    - lecture_ids: Generate from all quizzes in specific lectures
    - neither: Generate from user's incorrect/unanswered questions (original behavior)
    """
    service = PracticeQuizService(db)

    # Determine generation mode
    if request.quiz_ids:
        # Generate from specific quizzes
        if not request.course_id:
            raise HTTPException(
                status_code=400,
                detail="course_id is required when selecting specific quizzes",
            )

        questions = service.get_questions_from_quizzes(
            quiz_ids=request.quiz_ids,
            question_count=request.question_count,
        )

        if not questions:
            raise HTTPException(
                status_code=404,
                detail=f"No quiz questions found in the selected quizzes: {request.quiz_ids}",
            )

        error_message = f" for selected quizzes {request.quiz_ids}"
    elif request.lecture_ids:
        # Generate from specific lectures
        questions = service.get_questions_from_lectures(
            lecture_ids=request.lecture_ids,
            question_count=request.question_count,
        )

        if not questions:
            raise HTTPException(
                status_code=404,
                detail=f"No quiz questions found in the selected lectures: {request.lecture_ids}",
            )

        error_message = f" for selected lectures {request.lecture_ids}"
    else:
        # Generate from incorrect/unanswered questions (original behavior)
        questions = service.get_incorrect_questions(
            user_id=current_user.id,
            course_id=request.course_id,
            question_count=request.question_count,
            include_unanswered=request.include_unanswered,
        )

        if not questions:
            raise HTTPException(
                status_code=404,
                detail="No incorrect or unanswered questions found"
                + (f" for course {request.course_id}" if request.course_id else ""),
            )

        error_message = f" for course {request.course_id}" if request.course_id else ""

    # Create practice quiz (user-specific, not in course content)
    practice_quiz = service.create_practice_content(
        user_id=current_user.id,
        questions=questions,
        course_id=request.course_id,
        lecture_ids=request.lecture_ids,
        quiz_ids=request.quiz_ids,
    )

    # Get questions without answers for the attempt
    attempt_data = service.start_practice_attempt(
        practice_quiz_id=practice_quiz.id,
        user_id=current_user.id,
    )

    return {
        "practice_quiz_id": practice_quiz.id,
        "title": practice_quiz.title,
        "description": practice_quiz.description,
        "questions": attempt_data["questions"],
        "total_questions": practice_quiz.total_questions,
        "started_at": attempt_data["started_at"],
        "message": f"Practice quiz generated with {practice_quiz.total_questions} questions",
    }


@router.get("/me/practice-quiz/{practice_quiz_id}/questions")
def get_practice_quiz_questions(
    practice_quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get practice quiz questions by practice_id.
    Returns questions without correct answers for the user to attempt.
    """
    from app.models.practice_quiz import PracticeQuiz

    # Get the practice quiz
    practice_quiz = (
        db.query(PracticeQuiz)
        .filter(
            PracticeQuiz.id == practice_quiz_id,
            PracticeQuiz.user_id == current_user.id,
        )
        .first()
    )

    if not practice_quiz:
        raise HTTPException(
            status_code=404,
            detail="Practice quiz not found",
        )

    # Check if already completed
    if practice_quiz.is_completed:
        raise HTTPException(
            status_code=400,
            detail="This practice quiz has already been completed. Use the result endpoint to see your answers.",
        )

    # Get questions without correct answers
    questions_without_answers = []
    if practice_quiz.questions:
        for idx, question in enumerate(practice_quiz.questions):
            questions_without_answers.append(
                {
                    "question_index": idx,
                    "question": question["question"],
                    "options": question["options"],
                    "question_type": question.get("question_type", "multiple_choice"),
                }
            )

    return {
        "practice_quiz_id": practice_quiz.id,
        "title": practice_quiz.title,
        "description": practice_quiz.description,
        "questions": questions_without_answers,
        "total_questions": practice_quiz.total_questions,
        "started_at": practice_quiz.created_at,
    }


@router.post(
    "/me/practice-quiz/{practice_quiz_id}/submit",
    response_model=PracticeQuizDetailedResultResponse,
)
def submit_practice_quiz(
    practice_quiz_id: int,
    answers: List[dict] = Body(...),
    time_taken: int = Body(..., ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a practice quiz.
    Always shows correct answers and explanations after submission.
    """
    service = PracticeQuizService(db)

    # Submit and get results
    practice_quiz = service.submit_practice_attempt(
        practice_quiz_id=practice_quiz_id,
        user_id=current_user.id,
        answers=answers,
        time_taken=time_taken,
    )

    # Build detailed results with correct answers
    questions_with_results = []
    if practice_quiz.questions and practice_quiz.answers:
        answer_map = {ans["question_index"]: ans for ans in practice_quiz.answers}

        for idx, question in enumerate(practice_quiz.questions):
            answer_data = answer_map.get(idx, {})

            result = {
                "question": question["question"],
                "options": question["options"],
                "user_answer": answer_data.get("selected_answer"),
                "correct_answer": question["correct_answer"],
                "is_correct": answer_data.get("is_correct", False),
                "explanation_en": question.get("explanation_en"),
                "explanation_ar": question.get("explanation_ar"),
                "source_course_id": question.get("source_course_id"),
                "source_lecture_id": question.get("source_lecture_id"),
                "source_quiz_title": question.get("source_quiz_title"),
            }

            questions_with_results.append(result)

    return {
        "id": practice_quiz.id,
        "course_id": practice_quiz.course_id,
        "title": practice_quiz.title,
        "description": practice_quiz.description,
        "total_questions": practice_quiz.total_questions,
        "score": practice_quiz.score,
        "correct_answers": practice_quiz.correct_answers,
        "time_taken": practice_quiz.time_taken,
        "is_completed": practice_quiz.is_completed,
        "completed_at": practice_quiz.completed_at,
        "created_at": practice_quiz.created_at,
        "questions_with_results": questions_with_results,
    }


@router.get("/me/practice-quiz/result", response_model=PracticeQuizResultsListResponse)
def get_my_practice_quiz_results(
    course_id: Optional[int] = Query(None, description="Filter by course ID"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all practice quiz results for the current user.
    Returns completed and incomplete practice quizzes with pagination.
    """
    import math

    service = PracticeQuizService(db)

    # Get practice quizzes with pagination
    quizzes, total = service.get_user_practice_quizzes(
        user_id=current_user.id,
        course_id=course_id,
        page=page,
        size=size,
    )

    # Calculate total pages
    total_pages = math.ceil(total / size) if size > 0 else 0

    return {
        "results": quizzes,
        "total": total,
        "page": page,
        "size": size,
        "total_pages": total_pages,
    }


@router.get(
    "/me/practice-quiz/result/{practice_quiz_id}",
    response_model=PracticeQuizDetailedResultResponse,
)
def get_practice_quiz_detailed_result(
    practice_quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed results for a specific practice quiz.
    Includes all questions with user answers, correct answers, and explanations.
    """
    from app.models.practice_quiz import PracticeQuiz

    # Get the practice quiz
    practice_quiz = (
        db.query(PracticeQuiz)
        .filter(
            PracticeQuiz.id == practice_quiz_id,
            PracticeQuiz.user_id == current_user.id,
        )
        .first()
    )

    if not practice_quiz:
        raise HTTPException(
            status_code=404,
            detail="Practice quiz not found",
        )

    # Build questions with results if completed
    questions_with_results = None

    if practice_quiz.is_completed and practice_quiz.questions and practice_quiz.answers:
        questions_with_results = []

        # Create a mapping of question index to answer
        answer_map = {ans["question_index"]: ans for ans in practice_quiz.answers}

        for idx, question in enumerate(practice_quiz.questions):
            answer_data = answer_map.get(idx, {})

            result = {
                "question": question["question"],
                "options": question["options"],
                "user_answer": answer_data.get("selected_answer"),
                "correct_answer": question["correct_answer"],
                "is_correct": answer_data.get("is_correct", False),
                "explanation_en": question.get("explanation_en"),
                "explanation_ar": question.get("explanation_ar"),
                "source_course_id": question.get("source_course_id"),
                "source_lecture_id": question.get("source_lecture_id"),
                "source_quiz_title": question.get("source_quiz_title"),
            }

            questions_with_results.append(result)

    return {
        "id": practice_quiz.id,
        "course_id": practice_quiz.course_id,
        "title": practice_quiz.title,
        "description": practice_quiz.description,
        "total_questions": practice_quiz.total_questions,
        "score": practice_quiz.score,
        "correct_answers": practice_quiz.correct_answers,
        "time_taken": practice_quiz.time_taken,
        "is_completed": practice_quiz.is_completed,
        "completed_at": practice_quiz.completed_at,
        "created_at": practice_quiz.created_at,
        "questions_with_results": questions_with_results,
    }


# ==================== Course Enrollment Endpoints ====================


@router.post(
    "/me/enrollments", response_model=CourseEnrollmentResponse, status_code=201
)
def enroll_in_course(
    enrollment_data: CourseEnrollmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Enroll current user in a course.
    - Free courses are automatically enrolled
    - Paid courses require payment processing
    """
    service = CourseEnrollmentService(db)
    enrollment = service.enroll_user(current_user.id, enrollment_data)

    # Build response with course details
    return {
        "id": enrollment.id,
        "user_id": enrollment.user_id,
        "course_id": enrollment.course_id,
        "enrollment_type": enrollment.enrollment_type,
        "price_paid": enrollment.price_paid,
        "payment_reference": enrollment.payment_reference,
        "completed_lectures": enrollment.completed_lectures,
        "total_lectures": enrollment.total_lectures,
        "enrolled_at": enrollment.enrolled_at,
        "last_accessed_at": enrollment.last_accessed_at,
        "completed_at": enrollment.completed_at,
        "course_name": enrollment.course.name if enrollment.course else None,
        "course_image": enrollment.course.image if enrollment.course else None,
        "course_price": enrollment.course.price if enrollment.course else None,
    }


@router.get("/me/courses", response_model=EnrolledCoursesListResponse)
def get_my_courses(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all courses current user is enrolled in.
    Alias for /me/enrollments endpoint.
    Includes free and paid courses with progress tracking.
    """
    service = CourseEnrollmentService(db)
    enrollments, pagination = service.get_user_enrollments(current_user.id, page, size)

    # Build detailed response
    enrolled_courses = []
    for enrollment in enrollments:
        course = enrollment.course
        progress = (
            (enrollment.completed_lectures / enrollment.total_lectures * 100)
            if enrollment.total_lectures > 0
            else 0.0
        )

        enrolled_courses.append(
            {
                "id": enrollment.id,
                "user_id": enrollment.user_id,
                "course_id": enrollment.course_id,
                "enrollment_type": enrollment.enrollment_type,
                "price_paid": enrollment.price_paid,
                "completed_lectures": enrollment.completed_lectures,
                "total_lectures": enrollment.total_lectures,
                "progress_percentage": round(progress, 2),
                "enrolled_at": enrollment.enrolled_at,
                "last_accessed_at": enrollment.last_accessed_at,
                "completed_at": enrollment.completed_at,
                "course_name": course.name,
                "course_description": course.description,
                "course_image": course.image,
                "course_price": course.price,
                "course_is_free": course.is_free,
            }
        )

    return {
        "enrollments": enrolled_courses,
        **pagination,
    }


@router.get("/me/enrollments", response_model=EnrolledCoursesListResponse)
def get_my_enrolled_courses(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all courses current user is enrolled in.
    Includes free and paid courses with progress tracking.
    """
    service = CourseEnrollmentService(db)
    enrollments, pagination = service.get_user_enrollments(current_user.id, page, size)

    # Build detailed response
    enrolled_courses = []
    for enrollment in enrollments:
        course = enrollment.course
        progress = (
            (enrollment.completed_lectures / enrollment.total_lectures * 100)
            if enrollment.total_lectures > 0
            else 0.0
        )

        enrolled_courses.append(
            {
                "id": enrollment.id,
                "user_id": enrollment.user_id,
                "course_id": enrollment.course_id,
                "enrollment_type": enrollment.enrollment_type,
                "price_paid": enrollment.price_paid,
                "completed_lectures": enrollment.completed_lectures,
                "total_lectures": enrollment.total_lectures,
                "progress_percentage": round(progress, 2),
                "enrolled_at": enrollment.enrolled_at,
                "last_accessed_at": enrollment.last_accessed_at,
                "completed_at": enrollment.completed_at,
                "course_name": course.name,
                "course_description": course.description,
                "course_image": course.image,
                "course_price": course.price,
                "course_is_free": course.is_free,
            }
        )

    return {
        "enrollments": enrolled_courses,
        **pagination,
    }


@router.get("/me/enrollments/{course_id}", response_model=EnrolledCourseResponse)
def get_my_course_enrollment(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get enrollment details for a specific course.
    """
    service = CourseEnrollmentService(db)
    enrollment = service.get_enrollment(current_user.id, course_id)

    if not enrollment:
        raise HTTPException(
            status_code=404,
            detail="Enrollment not found",
        )

    course = enrollment.course
    progress = (
        (enrollment.completed_lectures / enrollment.total_lectures * 100)
        if enrollment.total_lectures > 0
        else 0.0
    )

    return {
        "id": enrollment.id,
        "user_id": enrollment.user_id,
        "course_id": enrollment.course_id,
        "enrollment_type": enrollment.enrollment_type,
        "price_paid": enrollment.price_paid,
        "completed_lectures": enrollment.completed_lectures,
        "total_lectures": enrollment.total_lectures,
        "progress_percentage": round(progress, 2),
        "enrolled_at": enrollment.enrolled_at,
        "last_accessed_at": enrollment.last_accessed_at,
        "completed_at": enrollment.completed_at,
        "course_name": course.name,
        "course_description": course.description,
        "course_image": course.image,
        "course_price": course.price,
        "course_is_free": course.is_free,
    }


@router.delete("/me/enrollments/{course_id}", status_code=204)
def unenroll_from_course(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Unenroll current user from a course.
    """
    service = CourseEnrollmentService(db)
    service.unenroll_user(current_user.id, course_id)
    return None
