# app/models/lecture_content.py
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class LectureContent(Base):
    __tablename__ = "lecture_contents"

    id = Column(Integer, primary_key=True, index=True)

    # Relationships
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False, index=True)

    # Content Type: video, photo, file, audio, link, quiz
    content_type = Column(String(50), nullable=False, index=True)

    # Content source (URL/path for video, photo, file, audio, link)
    # For quiz, this will be null and questions will be used instead
    source = Column(Text, nullable=True)

    # Video platform (only for content_type='video')
    # Supported: youtube, vdocipher, vimeo, custom, etc.
    video_platform = Column(
        String(50), nullable=True, default="youtube", server_default="youtube"
    )

    # Quiz questions (only for content_type='quiz')
    # Stored as JSON array: [{"question": "...", "options": [...], "answer": "..."}]
    questions = Column(JSONB, nullable=True)

    # Quiz settings (only for content_type='quiz')
    quiz_duration = Column(Integer, nullable=True)  # Quiz time limit in minutes
    max_attempts = Column(
        Integer, nullable=True
    )  # Maximum number of attempts allowed (null = unlimited)
    passing_score = Column(
        Integer, nullable=True
    )  # Passing score percentage (e.g., 70 for 70%)
    show_correct_answers = Column(
        Integer, default=1, nullable=False
    )  # Show correct answers after attempt (0 or 1)
    randomize_questions = Column(
        Integer, default=0, nullable=False
    )  # Randomize question order (0 or 1)
    randomize_options = Column(
        Integer, default=0, nullable=False
    )  # Randomize option order (0 or 1)

    # Optional metadata
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Order/Position in lecture
    position = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self):
        return f"<LectureContent(id={self.id}, type='{self.content_type}', lecture_id={self.lecture_id})>"
