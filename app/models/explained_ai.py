# app/models/explained_ai.py
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class ExplainedAI(Base):
    __tablename__ = "explained_ai"

    id = Column(Integer, primary_key=True, index=True)

    # User relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Content identification
    source = Column(
        String(255), nullable=False
    )  # Unique identifier (filename or topic name)
    content = Column(Text, nullable=False)  # The explained content (JSON string)

    # Sharing
    share_link = Column(String(255), unique=True, nullable=True)  # Unique share link
    is_shared = Column(Boolean, default=False, nullable=False)

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

    class Config:
        from_attributes = True

    def __repr__(self):
        return f"<ExplainedAI(id={self.id}, user_id={self.user_id}, source='{self.source}')>"
