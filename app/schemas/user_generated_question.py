# app/schemas/user_generated_question.py
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

# ==================== Question Generation Schemas ====================


class GenerateUserQuestionsRequest(BaseModel):
    """Request to generate questions from topic"""

    topic: str = Field(
        ..., min_length=3, max_length=500, description="Topic for questions"
    )
    title: str = Field(
        ..., min_length=3, max_length=255, description="Title for question set"
    )
    description: Optional[str] = Field(None, description="Optional description")
    difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$")
    question_type: str = Field(
        default="multiple_choice",
        pattern="^(multiple_choice|true_false|essay|mixed)$",
    )
    count: int = Field(default=5, ge=1, le=50, description="Number of questions")
    is_public: bool = Field(
        default=False, description="Make questions public for others"
    )
    notes: Optional[str] = Field(None, description="Additional instructions for AI")


class GenerateUserQuestionsFromPDFRequest(BaseModel):
    """Request metadata for generating questions from PDF"""

    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = Field(None)
    difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$")
    question_type: str = Field(
        default="multiple_choice",
        pattern="^(multiple_choice|true_false|essay|mixed)$",
    )
    count: int = Field(default=5, ge=1, le=50)
    is_public: bool = Field(default=False)
    notes: Optional[str] = Field(None)


class AddMoreQuestionsRequest(BaseModel):
    """Request to add more questions to existing set"""

    count: int = Field(
        default=5, ge=1, le=50, description="Number of additional questions"
    )
    notes: Optional[str] = Field(None, description="Additional instructions for AI")


# ==================== Response Schemas ====================


class QuestionDetail(BaseModel):
    """Single question detail"""

    question: str
    options: List[str]
    correct_answer: Optional[int] = None  # Hidden for attempts
    explanation_en: Optional[str] = None
    explanation_ar: Optional[str] = None
    question_type: Optional[str] = None


class UserGeneratedQuestionResponse(BaseModel):
    """Response for user generated question set"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    description: Optional[str]
    topic: str
    difficulty: str
    question_type: str
    is_public: bool
    total_questions: int
    source_type: str
    source_file_name: Optional[str]
    attempt_count: int
    created_at: datetime
    updated_at: datetime

    # User info
    creator_name: Optional[str] = None


class UserGeneratedQuestionDetailResponse(UserGeneratedQuestionResponse):
    """Detailed response with questions (for creator only)"""

    questions: List[QuestionDetail]


class UserGeneratedQuestionListResponse(BaseModel):
    """List of user generated questions with pagination"""

    question_sets: List[UserGeneratedQuestionResponse]
    total: int
    page: int
    size: int
    total_pages: int


# ==================== Attempt Schemas ====================


class StartAttemptResponse(BaseModel):
    """Response when starting an attempt"""

    attempt_id: int
    question_set_id: int
    title: str
    description: Optional[str]
    topic: str
    difficulty: str
    total_questions: int
    questions: List[QuestionDetail]  # Without correct answers
    started_at: datetime


class SubmitAttemptRequest(BaseModel):
    """Submit attempt answers"""

    answers: List[dict] = Field(
        ..., description="Array of {question_index, selected_answer}"
    )
    time_taken: int = Field(..., ge=0, description="Time taken in seconds")


class QuestionWithResult(BaseModel):
    """Question with user's answer and result"""

    question: str
    options: List[str]
    user_answer: Optional[int]
    correct_answer: int
    is_correct: bool
    explanation_en: Optional[str]
    explanation_ar: Optional[str]


class AttemptResultResponse(BaseModel):
    """Detailed attempt result"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    question_set_id: int
    user_id: int
    score: Optional[int]
    correct_answers: Optional[int]
    total_questions: int
    time_taken: Optional[int]
    is_completed: bool
    started_at: datetime
    completed_at: Optional[datetime]

    # Question set info
    title: str
    topic: str
    difficulty: str

    # Results
    questions_with_results: Optional[List[QuestionWithResult]] = None


class UserAttemptListResponse(BaseModel):
    """List of user's attempts"""

    attempts: List[AttemptResultResponse]
    total: int
    page: int
    size: int
    total_pages: int


# ==================== Public Question Schemas ====================


class PublicQuestionSetResponse(BaseModel):
    """Public question set for discovery"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str]
    topic: str
    difficulty: str
    question_type: str
    total_questions: int
    attempt_count: int
    created_at: datetime
    creator_name: str

    # User's attempt status
    user_has_attempted: bool = False
    user_best_score: Optional[int] = None
    user_has_pending_attempt: bool = False
    pending_attempt_id: Optional[int] = None
    pending_attempt_started_at: Optional[datetime] = None


class PublicQuestionListResponse(BaseModel):
    """List of public questions"""

    question_sets: List[PublicQuestionSetResponse]
    total: int
    page: int
    size: int
    total_pages: int


# ==================== Participant/Leaderboard Schemas ====================


class ParticipantResponse(BaseModel):
    """Participant who attempted a question set"""

    user_id: int
    user_name: str
    profile_picture: Optional[str] = None
    best_score: int
    total_attempts: int
    last_attempt_at: datetime
    rank: int


class ParticipantListResponse(BaseModel):
    """List of participants with leaderboard"""

    participants: List[ParticipantResponse]
    total_participants: int
    question_set_id: int
    question_set_title: str
    total_attempts: int
    page: int
    size: int
    total_pages: int


# ==================== Pending Attempt Schemas ====================


class PendingAttemptInfo(BaseModel):
    """Info about a pending (incomplete) attempt"""

    attempt_id: int
    question_set_id: int
    question_set_title: str
    question_set_topic: str
    difficulty: str
    total_questions: int
    started_at: datetime


class PendingAttemptsResponse(BaseModel):
    """List of all pending attempts for user"""

    pending_attempts: List[PendingAttemptInfo]
    total: int
