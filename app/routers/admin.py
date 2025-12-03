from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin, require_admin_level
from app.models.admin import Admin
from app.schemas.admin import (
    AdminResponse,
    CreateAdmin,
    CreateAdminResponse,
    ListOfAdminsResponse,
    UpdateAdmin,
)
from app.schemas.user import (
    AdminUserFullDetailsResponse,
    AdminUserGeneratedQuestionsResponse,
    AdminUserPracticeQuizzesResponse,
    AdminUserQuizAttemptsResponse,
    AdminUserUsageResponse,
    ListUsersResponse,
    UpdateUserRequest,
    UpdateUserStatusRequest,
    UserActivationRequest,
    UserManagementResponse,
)
from app.services.admin import AdminServices
from app.services.user import UserService

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    responses={404: {"description": "Not found"}},
)

admin_service = AdminServices()


@router.post(
    "/create",
    response_model=CreateAdminResponse,
    description="Create a new admin (requires super admin - level 999)",
    status_code=201,
)
async def create_admin(
    admin_data: CreateAdmin,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin_level(999)),
):
    """
    Create a new admin account. Only super admins (level 999) can create new admins.
    """
    return admin_service.create(admin_data, db)


@router.get(
    "/me",
    response_model=AdminResponse,
    description="Get current admin profile",
)
async def get_current_admin_profile(
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Get the current authenticated admin's profile information.
    """
    return AdminResponse.model_validate(current_admin)


@router.get(
    "/list",
    response_model=ListOfAdminsResponse,
    description="List all admins (requires super admin - level 999)",
)
async def list_admins(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin_level(999)),
):
    """
    Get a paginated list of all admins. Only super admins can access this endpoint.
    """
    return admin_service.get_all_admins(db, page, limit)


# ==================== User Management Endpoints ====================


@router.get(
    "/users",
    response_model=ListUsersResponse,
    description="List all users with pagination and search (requires admin access)",
)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(
        None, description="Search query for name, email, phone, or telegram info"
    ),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Get a paginated list of all users with optional search functionality.
    Requires admin access.
    """
    user_service = UserService(db)
    result = user_service.get_all_users(page=page, per_page=per_page, search=search)

    return {
        "users": result["users"],
        "total": result["total"],
        "page": result["page"],
        "per_page": result["per_page"],
        "total_pages": result["total_pages"],
        "has_next": result["has_next"],
        "has_prev": result["has_prev"],
        "next_page": result["next_page"],
        "prev_page": result["prev_page"],
    }


@router.get(
    "/users/{user_id}",
    response_model=UserManagementResponse,
    description="Get user by ID (requires admin access)",
)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Get a specific user by ID. Requires admin access.
    """
    user_service = UserService(db)
    user = user_service.get_user(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.put(
    "/users/{user_id}",
    response_model=UserManagementResponse,
    description="Update user information (requires admin access)",
)
async def update_user(
    user_id: int,
    user_data: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Update user information. Requires admin access.
    """
    user_service = UserService(db)
    update_data = user_data.model_dump(exclude_unset=True)

    user = user_service.update_user(user_id, update_data)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.put(
    "/users/{user_id}/status",
    response_model=UserManagementResponse,
    description="Update user status (requires admin access)",
)
async def update_user_status(
    user_id: int,
    status_data: UpdateUserStatusRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Update user status (student, teacher, admin, blocked, pending).
    Requires admin access.
    """
    user_service = UserService(db)
    user = user_service.update_user_status(user_id, status_data.status)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.put(
    "/users/{user_id}/activation",
    response_model=UserManagementResponse,
    description="Activate or deactivate user account (requires admin access)",
)
async def activate_deactivate_user(
    user_id: int,
    activation_data: UserActivationRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Activate or deactivate a user account. Requires admin access.
    """
    user_service = UserService(db)
    user = user_service.activate_deactivate_user(user_id, activation_data.is_active)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.delete(
    "/users/{user_id}",
    description="Delete user permanently (requires super admin - level 999)",
    status_code=200,
)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin_level(999)),
):
    """
    Delete a user permanently. Requires super admin level (999).
    """
    user_service = UserService(db)
    success = user_service.delete_user(user_id)

    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "User deleted successfully"}


# ==================== Admin Management Endpoints ====================


@router.get(
    "/{admin_id}",
    response_model=AdminResponse,
    description="Get admin by ID (requires super admin - level 999)",
)
async def get_admin(
    admin_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin_level(999)),
):
    """
    Get a specific admin by ID. Only super admins can access this endpoint.
    """
    return admin_service.get_admin_by_id(admin_id, db)


@router.put(
    "/{admin_id}",
    response_model=AdminResponse,
    description="Update admin details",
)
async def update_admin(
    admin_id: int,
    admin_data: UpdateAdmin,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Update admin details. Super admins can update any admin, regular admins can only update their own profile.
    """
    # Check permissions: super admin can update anyone, regular admin can only update self
    if current_admin.level < 999 and current_admin.id != admin_id:
        raise HTTPException(
            status_code=403, detail="You can only update your own profile"
        )

    # Prevent regular admins from changing their own level or verification status
    if current_admin.level < 999:
        if admin_data.level is not None:
            raise HTTPException(
                status_code=403, detail="You cannot change admin levels"
            )
        if admin_data.is_verified is not None:
            raise HTTPException(
                status_code=403, detail="You cannot change verification status"
            )

    return admin_service.update_admin(admin_id, admin_data, db)


@router.delete(
    "/{admin_id}",
    description="Delete admin (requires super admin - level 999)",
    status_code=200,
)
async def delete_admin(
    admin_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin_level(999)),
):
    """
    Delete an admin account. Only super admins can delete admins.
    Cannot delete super admin accounts.
    """
    # Prevent self-deletion
    if current_admin.id == admin_id:
        raise HTTPException(
            status_code=400, detail="You cannot delete your own account"
        )

    return admin_service.delete_admin(admin_id, db)


@router.post(
    "/{admin_id}/reset-password",
    description="Reset admin password (requires super admin - level 999)",
    status_code=200,
)
async def reset_admin_password(
    admin_id: int,
    new_password: str = Query(..., min_length=4, description="New password"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin_level(999)),
):
    """
    Reset an admin's password. Only super admins can reset passwords.
    """
    return admin_service.reset_admin_password(admin_id, new_password, db)


# ==================== User Details & Analytics Endpoints ====================


@router.get(
    "/users/{user_id}/details",
    response_model=AdminUserFullDetailsResponse,
    description="Get full user details with all statistics (requires admin access)",
)
async def get_user_full_details(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Get comprehensive user details including all statistics:
    - Basic user info
    - Quiz attempt statistics
    - Usage statistics
    - Generated questions statistics
    - Practice quiz statistics
    - Course enrollment statistics
    """
    import math
    from decimal import Decimal

    from sqlalchemy import func

    from app.models.course import Course
    from app.models.course_enrollment import CourseEnrollment
    from app.models.lecture_content import LectureContent
    from app.models.practice_quiz import PracticeQuiz
    from app.models.quiz_attempt import QuizAttempt
    from app.models.user import User
    from app.models.user_daily_usage import UserDailyUsage
    from app.models.user_generated_question import UserGeneratedQuestion

    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Quiz attempt statistics
    quiz_attempts = db.query(QuizAttempt).filter(QuizAttempt.user_id == user_id).all()
    completed_attempts = [a for a in quiz_attempts if a.is_completed == 1]
    avg_score = (
        sum(float(a.score or 0) for a in completed_attempts) / len(completed_attempts)
        if completed_attempts
        else 0
    )
    total_questions_answered = sum(a.total_questions for a in completed_attempts)
    total_correct = sum(a.correct_answers or 0 for a in completed_attempts)

    quiz_stats = {
        "total_attempts": len(quiz_attempts),
        "completed_attempts": len(completed_attempts),
        "avg_score": round(avg_score, 2),
        "total_questions_answered": total_questions_answered,
        "total_correct_answers": total_correct,
        "accuracy_rate": round(
            (
                (total_correct / total_questions_answered * 100)
                if total_questions_answered > 0
                else 0
            ),
            2,
        ),
    }

    # Usage statistics
    usage_records = (
        db.query(UserDailyUsage).filter(UserDailyUsage.user_id == user_id).all()
    )
    total_minutes = sum(u.minutes_spent for u in usage_records)
    usage_stats = {
        "total_days_active": len(usage_records),
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 2),
        "avg_minutes_per_day": (
            round(total_minutes / len(usage_records), 2) if usage_records else 0
        ),
    }

    # Generated questions statistics
    generated_questions = (
        db.query(UserGeneratedQuestion)
        .filter(UserGeneratedQuestion.user_id == user_id)
        .all()
    )
    public_count = len([q for q in generated_questions if q.is_public])
    total_questions_count = sum(q.total_questions for q in generated_questions)

    generated_questions_stats = {
        "total_sets_generated": len(generated_questions),
        "total_questions_generated": total_questions_count,
        "public_count": public_count,
        "private_count": len(generated_questions) - public_count,
        "total_attempts_by_others": sum(q.attempt_count for q in generated_questions),
    }

    # Practice quiz statistics
    practice_quizzes = (
        db.query(PracticeQuiz).filter(PracticeQuiz.user_id == user_id).all()
    )
    completed_practice = [p for p in practice_quizzes if p.is_completed]
    avg_practice_score = (
        sum(float(p.score or 0) for p in completed_practice) / len(completed_practice)
        if completed_practice
        else 0
    )

    practice_quiz_stats = {
        "total_practice_quizzes": len(practice_quizzes),
        "completed_count": len(completed_practice),
        "incomplete_count": len(practice_quizzes) - len(completed_practice),
        "avg_score": round(avg_practice_score, 2),
        "total_questions_practiced": sum(p.total_questions for p in practice_quizzes),
    }

    # Enrollment statistics
    enrollments = (
        db.query(CourseEnrollment).filter(CourseEnrollment.user_id == user_id).all()
    )
    completed_courses = len([e for e in enrollments if e.is_completed])

    enrollment_stats = {
        "total_enrolled_courses": len(enrollments),
        "completed_courses": completed_courses,
        "in_progress_courses": len(enrollments) - completed_courses,
        "avg_progress": (
            round(
                sum(float(e.progress or 0) for e in enrollments) / len(enrollments), 2
            )
            if enrollments
            else 0
        ),
    }

    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "parent_phone_number": user.parent_phone_number,
        "academic_id": user.academic_id,
        "profile_picture": user.profile_picture,
        "telegram_id": user.telegram_id,
        "telegram_username": user.telegram_username,
        "telegram_first_name": user.telegram_first_name,
        "telegram_last_name": user.telegram_last_name,
        "sex": user.sex,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "status": user.status,
        "wallet_balance": user.wallet_balance,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "last_login": user.last_login,
        "telegram_verified_at": user.telegram_verified_at,
        "quiz_stats": quiz_stats,
        "usage_stats": usage_stats,
        "generated_questions_stats": generated_questions_stats,
        "practice_quiz_stats": practice_quiz_stats,
        "enrollment_stats": enrollment_stats,
    }


@router.get(
    "/users/{user_id}/quiz-attempts",
    response_model=AdminUserQuizAttemptsResponse,
    description="Get user quiz attempts with pagination (requires admin access)",
)
async def get_user_quiz_attempts(
    user_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    course_id: Optional[int] = Query(None, description="Filter by course ID"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Get paginated list of user's quiz attempts with statistics.
    """
    import math

    from app.models.lecture_content import LectureContent
    from app.models.quiz_attempt import QuizAttempt
    from app.models.user import User

    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Build query
    query = db.query(QuizAttempt).filter(QuizAttempt.user_id == user_id)
    if course_id:
        query = query.filter(QuizAttempt.course_id == course_id)

    # Get total
    total = query.count()

    # Get paginated results
    offset = (page - 1) * size
    attempts = (
        query.order_by(QuizAttempt.created_at.desc()).offset(offset).limit(size).all()
    )

    # Build response with quiz titles
    attempts_list = []
    for attempt in attempts:
        content = (
            db.query(LectureContent)
            .filter(LectureContent.id == attempt.content_id)
            .first()
        )
        attempts_list.append(
            {
                "id": attempt.id,
                "content_id": attempt.content_id,
                "course_id": attempt.course_id,
                "lecture_id": attempt.lecture_id,
                "quiz_title": content.title if content else None,
                "score": attempt.score,
                "total_questions": attempt.total_questions,
                "correct_answers": attempt.correct_answers,
                "time_taken": attempt.time_taken,
                "is_completed": attempt.is_completed,
                "started_at": attempt.started_at,
                "completed_at": attempt.completed_at,
            }
        )

    # Calculate stats
    completed_attempts = [a for a in attempts if a.is_completed == 1]
    avg_score = (
        sum(float(a.score or 0) for a in completed_attempts) / len(completed_attempts)
        if completed_attempts
        else 0
    )

    return {
        "user_id": user_id,
        "user_name": user.full_name,
        "attempts": attempts_list,
        "total": total,
        "page": page,
        "size": size,
        "total_pages": math.ceil(total / size) if size > 0 else 0,
        "stats": {
            "avg_score": round(avg_score, 2),
            "total_completed": len(completed_attempts),
            "total_in_progress": len(attempts) - len(completed_attempts),
        },
    }


@router.get(
    "/users/{user_id}/generated-questions",
    response_model=AdminUserGeneratedQuestionsResponse,
    description="Get user generated questions with pagination (requires admin access)",
)
async def get_user_generated_questions(
    user_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Get paginated list of user's generated questions.
    """
    import math

    from app.models.user import User
    from app.models.user_generated_question import UserGeneratedQuestion

    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Build query
    query = db.query(UserGeneratedQuestion).filter(
        UserGeneratedQuestion.user_id == user_id
    )

    # Get total
    total = query.count()

    # Get paginated results
    offset = (page - 1) * size
    questions = (
        query.order_by(UserGeneratedQuestion.created_at.desc())
        .offset(offset)
        .limit(size)
        .all()
    )

    # Build response
    questions_list = [
        {
            "id": q.id,
            "title": q.title,
            "topic": q.topic,
            "difficulty": q.difficulty,
            "question_type": q.question_type,
            "total_questions": q.total_questions,
            "is_public": q.is_public,
            "source_type": q.source_type,
            "attempt_count": q.attempt_count,
            "created_at": q.created_at,
        }
        for q in questions
    ]

    # Calculate stats
    public_count = len([q for q in questions if q.is_public])
    total_questions_count = sum(q.total_questions for q in questions)

    return {
        "user_id": user_id,
        "user_name": user.full_name,
        "questions": questions_list,
        "total": total,
        "page": page,
        "size": size,
        "total_pages": math.ceil(total / size) if size > 0 else 0,
        "stats": {
            "total_sets": len(questions),
            "total_questions_generated": total_questions_count,
            "public_count": public_count,
            "private_count": len(questions) - public_count,
        },
    }


@router.get(
    "/users/{user_id}/usage",
    response_model=AdminUserUsageResponse,
    description="Get user usage statistics with pagination (requires admin access)",
)
async def get_user_usage(
    user_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Get paginated list of user's daily usage records.
    """
    import math

    from app.models.user import User
    from app.models.user_daily_usage import UserDailyUsage

    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Build query
    query = db.query(UserDailyUsage).filter(UserDailyUsage.user_id == user_id)

    # Get total
    total = query.count()

    # Get all records for stats
    all_records = query.all()
    total_minutes = sum(u.minutes_spent for u in all_records)

    # Get paginated results
    offset = (page - 1) * size
    usage_records = (
        query.order_by(UserDailyUsage.date.desc()).offset(offset).limit(size).all()
    )

    # Build response
    usage_list = [
        {
            "date": u.date,
            "minutes_spent": u.minutes_spent,
        }
        for u in usage_records
    ]

    return {
        "user_id": user_id,
        "user_name": user.full_name,
        "usage": usage_list,
        "total_days": total,
        "total_minutes": total_minutes,
        "avg_minutes_per_day": round(total_minutes / total, 2) if total > 0 else 0,
        "page": page,
        "size": size,
        "total_pages": math.ceil(total / size) if size > 0 else 0,
    }


@router.get(
    "/users/{user_id}/practice-quizzes",
    response_model=AdminUserPracticeQuizzesResponse,
    description="Get user practice quizzes with pagination (requires admin access)",
)
async def get_user_practice_quizzes(
    user_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Get paginated list of user's practice quizzes.
    """
    import math

    from app.models.practice_quiz import PracticeQuiz
    from app.models.user import User

    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Build query
    query = db.query(PracticeQuiz).filter(PracticeQuiz.user_id == user_id)

    # Get total
    total = query.count()

    # Get paginated results
    offset = (page - 1) * size
    practice_quizzes = (
        query.order_by(PracticeQuiz.created_at.desc()).offset(offset).limit(size).all()
    )

    # Build response
    quizzes_list = [
        {
            "id": p.id,
            "title": p.title,
            "course_id": p.course_id,
            "total_questions": p.total_questions,
            "score": p.score,
            "correct_answers": p.correct_answers,
            "time_taken": p.time_taken,
            "is_completed": p.is_completed,
            "created_at": p.created_at,
            "completed_at": p.completed_at,
        }
        for p in practice_quizzes
    ]

    # Calculate stats
    completed = [p for p in practice_quizzes if p.is_completed]
    avg_score = (
        sum(float(p.score or 0) for p in completed) / len(completed) if completed else 0
    )

    return {
        "user_id": user_id,
        "user_name": user.full_name,
        "practice_quizzes": quizzes_list,
        "total": total,
        "page": page,
        "size": size,
        "total_pages": math.ceil(total / size) if size > 0 else 0,
        "stats": {
            "total_practice_quizzes": len(practice_quizzes),
            "completed_count": len(completed),
            "avg_score": round(avg_score, 2),
        },
    }
