# app/models/post_reaction.py
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class PostReaction(Base):
    __tablename__ = "post_reactions"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Reaction Type
    reaction_type = Column(
        String(20), default="like", nullable=False
    )  # 'like', 'love', 'laugh', etc.

    # Timestamp
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Unique constraint: one user can only react once per post (can change reaction type)
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="unique_post_reaction"),
    )

    def __repr__(self):
        return f"<PostReaction(post_id={self.post_id}, user_id={self.user_id}, type='{self.reaction_type}')>"
