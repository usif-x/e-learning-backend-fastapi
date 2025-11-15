# app/schemas/lecture.py
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

# ==================== Lecture Content Schemas ====================


class QuizQuestion(BaseModel):
    """Schema for a single quiz question - ADMIN ONLY (includes correct answers)"""

    question: str
    options: List[str]
    correct_answer: int = Field(
        ..., ge=0, description="Index of the correct answer in options array"
    )
    explanation_en: str = Field(..., description="English explanation of the answer")
    explanation_ar: str = Field(..., description="Arabic explanation of the answer")


class QuizQuestionForAttempt(BaseModel):
    """Schema for quiz question during attempt - WITHOUT correct answer"""

    question: str
    options: List[str]


class QuizQuestionWithResult(BaseModel):
    """Schema for quiz question with result after submission"""

    question: str
    options: List[str]
    user_answer: Optional[int] = None  # None if question was unanswered
    correct_answer: int
    is_correct: bool
    explanation_en: Optional[str] = None
    explanation_ar: Optional[str] = None


class LectureContentBase(BaseModel):
    content_type: str = Field(..., pattern="^(video|photo|file|audio|link|quiz)$")
    source: Optional[str] = None
    video_platform: Optional[str] = Field(
        None,
        max_length=50,
        description="Video platform: youtube, vdocipher, vimeo, custom, etc.",
    )
    questions: Optional[List[QuizQuestion]] = None

    # Quiz settings (only for content_type='quiz')
    quiz_duration: Optional[int] = Field(
        None, ge=1, description="Quiz time limit in minutes"
    )
    max_attempts: Optional[int] = Field(
        None, ge=1, description="Maximum attempts allowed (null = unlimited)"
    )
    passing_score: Optional[int] = Field(
        None, ge=0, le=100, description="Passing score percentage"
    )
    show_correct_answers: int = Field(
        default=1, ge=0, le=1, description="Show correct answers after attempt"
    )
    randomize_questions: int = Field(
        default=0, ge=0, le=1, description="Randomize question order"
    )
    randomize_options: int = Field(
        default=0, ge=0, le=1, description="Randomize option order"
    )

    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    position: int = Field(default=0, ge=0)


class LectureContentCreate(LectureContentBase):
    pass


class LectureContentUpdate(BaseModel):
    content_type: Optional[str] = Field(
        None, pattern="^(video|photo|file|audio|link|quiz)$"
    )
    source: Optional[str] = None
    video_platform: Optional[str] = Field(None, max_length=50)
    questions: Optional[List[QuizQuestion]] = None

    # Quiz settings
    quiz_duration: Optional[int] = Field(None, ge=1)
    max_attempts: Optional[int] = Field(None, ge=1)
    passing_score: Optional[int] = Field(None, ge=0, le=100)
    show_correct_answers: Optional[int] = Field(None, ge=0, le=1)
    randomize_questions: Optional[int] = Field(None, ge=0, le=1)
    randomize_options: Optional[int] = Field(None, ge=0, le=1)

    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    position: Optional[int] = Field(None, ge=0)


class LectureContentResponse(BaseModel):
    """Response for lecture content - excludes quiz questions for security"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    lecture_id: int
    content_type: str
    source: Optional[str] = None
    video_platform: Optional[str] = None

    # Quiz settings (questions excluded for security)
    quiz_duration: Optional[int] = None
    max_attempts: Optional[int] = None
    passing_score: Optional[int] = None
    show_correct_answers: int = 1
    randomize_questions: int = 0
    randomize_options: int = 0

    title: Optional[str] = None
    description: Optional[str] = None
    position: int
    created_at: datetime
    updated_at: datetime


class QuizContentResponse(LectureContentResponse):
    """Response for quiz content when starting an attempt - includes questions WITHOUT answers"""

    questions: Optional[List[QuizQuestionForAttempt]] = None


# ==================== Lecture Schemas ====================


class LectureBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    position: int = Field(default=0, ge=0)


class LectureCreate(LectureBase):
    pass


class LectureUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    position: Optional[int] = Field(None, ge=0)


class LectureResponse(LectureBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    created_at: datetime
    updated_at: datetime

    # Nested contents
    contents: List[LectureContentResponse] = []


class LectureListResponse(BaseModel):
    lectures: List[LectureResponse]
    total: int
    page: int
    size: int
    total_pages: int


# ==================== Content List Response ====================


class LectureContentListResponse(BaseModel):
    contents: List[LectureContentResponse]
    total: int
    page: int
    size: int
    total_pages: int


# ==================== Quiz Attempt Schemas ====================


class QuizAnswer(BaseModel):
    """User's answer for a quiz question"""

    question_index: int = Field(..., ge=0, description="Index of the question")
    selected_answer: Optional[int] = Field(
        None, ge=0, description="Index of the selected answer (null if unanswered)"
    )


class QuizAttemptCreate(BaseModel):
    """Submit quiz attempt"""

    answers: List[QuizAnswer]
    time_taken: int = Field(..., ge=0, description="Time taken in seconds")
    started_at: datetime
    attempt_id: Optional[int] = Field(
        None, description="ID of existing incomplete attempt to complete"
    )


class QuizAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    content_id: int
    course_id: int
    lecture_id: int
    score: Optional[float] = None
    total_questions: int
    correct_answers: Optional[int] = None
    time_taken: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    is_completed: int

    # Detailed results with correct answers (shown based on quiz settings)
    questions_with_results: Optional[List[QuizQuestionWithResult]] = None
    show_correct_answers: bool = True


class QuizAttemptListResponse(BaseModel):
    incomplete_attempt: Optional[QuizAttemptResponse] = None
    completed_attempts: List[QuizAttemptResponse]
    total: int
    page: int
    size: int
    total_pages: int


class QuizAttemptStats(BaseModel):
    """Statistics for a user's quiz attempts"""

    content_id: int
    total_attempts: int
    best_score: Optional[float] = None
    average_score: Optional[float] = None
    last_attempt_at: Optional[datetime] = None
    passed: bool = False


class StartQuizResponse(BaseModel):
    """Response when starting a quiz attempt with questions"""

    content: QuizContentResponse
    attempt_id: int
    attempts_used: int
    attempts_remaining: Optional[int] = None
    can_attempt: bool
    message: Optional[str] = None


# ==================== AI Quiz Generation Schemas ====================


class GenerateQuizRequest(BaseModel):
    """Request to generate quiz questions using AI"""

    lecture_id: int = Field(..., description="Lecture ID to associate quiz with")
    topic: str = Field(
        ..., min_length=3, max_length=500, description="Topic for quiz questions"
    )
    difficulty: str = Field(
        default="medium",
        pattern="^(easy|medium|hard)$",
        description="Question difficulty level",
    )
    count: int = Field(
        default=5, ge=1, le=20, description="Number of questions to generate"
    )


class GenerateQuizResponse(BaseModel):
    """Response containing AI-generated quiz questions"""

    success: bool
    topic: str
    questions: List[QuizQuestion]


# ==================== User Quiz Analytics Schemas ====================


class UserQuizAnalytics(BaseModel):
    """Analytics for user's quiz performance"""

    model_config = ConfigDict(from_attributes=True)

    # Quiz info
    content_id: int
    quiz_title: Optional[str] = None
    course_id: int
    lecture_id: int

    # Attempt info
    attempt_id: int
    score: Optional[float] = None
    total_questions: int
    correct_answers: Optional[int] = None
    time_taken: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    is_completed: int

    # Detailed results (shown based on quiz settings)
    questions_with_results: Optional[List[QuizQuestionWithResult]] = None


class UserAllQuizzesAnalytics(BaseModel):
    """List of all user's quiz attempts with analytics"""

    quizzes: List[UserQuizAnalytics]
    total: int
    page: int
    size: int
    total_pages: int
