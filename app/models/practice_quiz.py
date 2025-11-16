# app/models/practice_quiz.py
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class PracticeQuiz(Base):
    __tablename__ = "practice_quizzes"

    id = Column(Integer, primary_key=True, index=True)

    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(
        Integer, ForeignKey("courses.id"), nullable=True, index=True
    )  # Null if mixed courses

    # Practice quiz metadata
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    # Quiz content
    questions = Column(
        JSONB, nullable=False
    )  # Array of questions with answers and explanations
    total_questions = Column(Integer, nullable=False)

    # Attempt data (from the completed attempt)
    attempt_id = Column(
        Integer, ForeignKey("quiz_attempts.id"), nullable=True
    )  # Link to the quiz attempt
    answers = Column(
        JSONB, nullable=True
    )  # User's answers: [{"question_index": 0, "selected_answer": 1, "is_correct": bool}, ...]
    score = Column(Numeric(5, 2), nullable=True)  # Score achieved (e.g., 85.50)
    correct_answers = Column(Integer, nullable=True)
    time_taken = Column(Integer, nullable=True)  # Time taken in seconds

    # Completion status
    is_completed = Column(
        Integer, default=0, nullable=False
    )  # 0 = generated, 1 = completed
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return (
            f"<PracticeQuiz(id={self.id}, user_id={self.user_id}, score={self.score})>"
        )
