# app/schemas/user.py

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    full_name: str
    telegram_id: str
    telegram_username: Optional[str] = None
    phone_number: Optional[str] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    status: str
    wallet_balance: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(BaseModel):
    """Detailed user profile for current user"""

    id: int
    full_name: str
    email: Optional[str]
    phone_number: Optional[str]
    parent_phone_number: Optional[str]
    profile_picture: Optional[str]
    telegram_id: str
    telegram_username: Optional[str]
    telegram_first_name: str
    telegram_last_name: Optional[str]
    is_active: bool
    is_verified: bool
    status: str
    wallet_balance: Decimal
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]
    telegram_verified_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class UpdatePasswordRequest(BaseModel):
    """Request to update user password"""

    current_password: str
    new_password: str
    confirm_password: str


class ForgotPasswordRequest(BaseModel):
    """Request to initiate password reset"""

    phone_number: str  # User's phone number


class VerifyResetCodeRequest(BaseModel):
    """Request to verify reset code"""

    phone_number: str  # User's phone number
    code: str  # 6-digit verification code


class ResetPasswordRequest(BaseModel):
    """Request to reset password with verification code"""

    phone_number: str  # User's phone number
    code: str  # 6-digit verification code
    new_password: str
    confirm_password: str


# User Management Schemas (for admin use)


class UserManagementResponse(BaseModel):
    """User response for admin management"""

    id: int
    full_name: str
    email: Optional[str]
    phone_number: Optional[str]
    telegram_id: str
    telegram_username: Optional[str]
    is_active: bool
    status: str
    wallet_balance: Decimal
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class UpdateUserRequest(BaseModel):
    """Request to update user information (admin only)"""

    full_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    telegram_username: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None
    wallet_balance: Optional[Decimal] = None


class UpdateUserStatusRequest(BaseModel):
    """Request to update user status"""

    status: str  # 'student', 'teacher', 'admin', 'blocked', 'pending'


class UserActivationRequest(BaseModel):
    """Request to activate/deactivate user account"""

    is_active: bool


class ListUsersResponse(BaseModel):
    """Paginated list of users for admin management"""

    users: list[UserManagementResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool
    next_page: Optional[int] = None
    prev_page: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== Admin User Details Schemas ====================


class UserQuizAttemptSummary(BaseModel):
    """Summary of a quiz attempt for admin view"""

    id: int
    content_id: int
    course_id: int
    lecture_id: int
    quiz_title: Optional[str] = None
    score: Optional[Decimal] = None
    total_questions: int
    correct_answers: Optional[int] = None
    time_taken: Optional[int] = None
    is_completed: int
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserGeneratedQuestionSummary(BaseModel):
    """Summary of user generated questions for admin view"""

    id: int
    title: str
    topic: str
    difficulty: str
    question_type: str
    total_questions: int
    is_public: bool
    source_type: str
    attempt_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUsageSummary(BaseModel):
    """Summary of user daily usage for admin view"""

    date: datetime
    minutes_spent: int

    model_config = ConfigDict(from_attributes=True)


class UserPracticeQuizSummary(BaseModel):
    """Summary of practice quiz for admin view"""

    id: int
    title: str
    course_id: Optional[int] = None
    total_questions: int
    score: Optional[Decimal] = None
    correct_answers: Optional[int] = None
    time_taken: Optional[int] = None
    is_completed: bool
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserEnrollmentSummary(BaseModel):
    """Summary of course enrollment for admin view"""

    course_id: int
    course_title: Optional[str] = None
    enrollment_type: str = "free"
    enrolled_at: datetime
    completed_lectures: int = 0
    total_lectures: int = 0
    progress_percentage: float = 0.0
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AdminUserQuizAttemptsResponse(BaseModel):
    """Response for user quiz attempts for admin"""

    user_id: int
    user_name: str
    attempts: list[UserQuizAttemptSummary]
    total: int
    page: int
    size: int
    total_pages: int
    stats: dict  # Contains avg_score, total_completed, total_questions_answered, etc.

    model_config = ConfigDict(from_attributes=True)


class AdminUserGeneratedQuestionsResponse(BaseModel):
    """Response for user generated questions for admin"""

    user_id: int
    user_name: str
    questions: list[UserGeneratedQuestionSummary]
    total: int
    page: int
    size: int
    total_pages: int
    stats: dict  # Contains total_questions_generated, public_count, etc.

    model_config = ConfigDict(from_attributes=True)


class AdminUserUsageResponse(BaseModel):
    """Response for user usage data for admin"""

    user_id: int
    user_name: str
    usage: list[UserUsageSummary]
    total_days: int
    total_minutes: int
    avg_minutes_per_day: float
    page: int
    size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


class AdminUserPracticeQuizzesResponse(BaseModel):
    """Response for user practice quizzes for admin"""

    user_id: int
    user_name: str
    practice_quizzes: list[UserPracticeQuizSummary]
    total: int
    page: int
    size: int
    total_pages: int
    stats: dict

    model_config = ConfigDict(from_attributes=True)


class AdminUserFullDetailsResponse(BaseModel):
    """Full user details for admin including all stats"""

    # Basic user info
    id: int
    full_name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    parent_phone_number: Optional[str] = None
    academic_id: Optional[str] = None
    profile_picture: Optional[str] = None
    telegram_id: str
    telegram_username: Optional[str] = None
    telegram_first_name: str
    telegram_last_name: Optional[str] = None
    sex: Optional[str] = None
    is_active: bool
    is_verified: bool
    status: str
    wallet_balance: Decimal
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    telegram_verified_at: Optional[datetime] = None

    # Statistics
    quiz_stats: dict  # avg_score, total_attempts, completed_attempts, etc.
    usage_stats: dict  # total_minutes, avg_per_day, etc.
    generated_questions_stats: dict  # total_generated, public_count, etc.
    practice_quiz_stats: dict  # total_practice, completed_count, avg_score, etc.
    enrollment_stats: dict  # total_enrolled, completed_courses, etc.

    model_config = ConfigDict(from_attributes=True)
