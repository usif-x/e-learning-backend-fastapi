# app/models/quiz_attempt.py
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)

    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content_id = Column(
        Integer, ForeignKey("lecture_contents.id"), nullable=False, index=True
    )
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False, index=True)

    # Attempt data
    answers = Column(
        JSONB, nullable=True
    )  # User's answers: [{"question_index": 0, "selected_answer": 1}, ...] (null if incomplete)
    score = Column(
        Numeric(5, 2), nullable=True
    )  # Score achieved (e.g., 85.50 for 85.5%) (null if incomplete)
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=True)  # Null if incomplete

    # Time tracking
    time_taken = Column(
        Integer, nullable=True
    )  # Time taken in seconds (null if incomplete)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(
        DateTime(timezone=True), nullable=True  # Null if attempt is incomplete
    )
    is_completed = Column(
        Integer, default=0, nullable=False  # 0 = in progress, 1 = completed
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self):
        return (
            f"<QuizAttempt(id={self.id}, user_id={self.user_id}, score={self.score})>"
        )
