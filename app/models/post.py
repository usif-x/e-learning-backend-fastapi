# app/models/post.py
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    community_id = Column(
        Integer, ForeignKey("communities.id"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Content
    content = Column(Text, nullable=True)  # Text content (optional if only media)

    # Post Settings
    is_pinned = Column(Boolean, default=False, nullable=False)
    is_edited = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Moderation Status: pending, accepted, rejected
    post_status = Column(String(20), default="pending", nullable=False, index=True)

    # Statistics
    reactions_count = Column(Integer, default=0, nullable=False)
    comments_count = Column(Integer, default=0, nullable=False)

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
        return f"<Post(id={self.id}, community_id={self.community_id}, user_id={self.user_id})>"
