# app/models/comment.py
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    parent_comment_id = Column(
        Integer, ForeignKey("comments.id"), nullable=True
    )  # For nested replies

    # Content
    content = Column(Text, nullable=False)

    # Comment Settings
    is_edited = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Statistics
    reactions_count = Column(Integer, default=0, nullable=False)

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
    edited_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return (
            f"<Comment(id={self.id}, post_id={self.post_id}, user_id={self.user_id})>"
        )
