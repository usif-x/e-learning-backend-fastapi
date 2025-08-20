# app/models/lecture_content.py
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class LectureContent(Base):
    __tablename__ = "lecture_contents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # e.g., "video", "file", "exam", "homework"
    content_type = Column(String(50), nullable=False)

    # URL to the video, path to the file, or ID of the exam
    content_source = Column(Text, nullable=False)

    # For future logic: is this content freely accessible or does it require completion of a dependency?
    is_opened = Column(Boolean, default=True, nullable=False)

    # Critical for ordering content within a lecture
    position = Column(Integer, nullable=False, default=0)

    # Link to the parent lecture
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False, index=True)

    # FOR FUTURE USE: To handle "pass exam to open next content"
    # This creates a self-referencing relationship.
    depends_on_content_id = Column(
        Integer, ForeignKey("lecture_contents.id"), nullable=True
    )

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
