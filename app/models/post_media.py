# app/models/post_media.py
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class PostMedia(Base):
    __tablename__ = "post_media"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign Key
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)

    # Media Info
    media_type = Column(String(20), nullable=False)  # 'image', 'audio'
    media_url = Column(Text, nullable=False)  # Storage path (e.g., 'posts/uuid.jpg')
    file_size = Column(Integer, nullable=True)  # File size in bytes
    duration = Column(Integer, nullable=True)  # Duration in seconds (for audio)

    # Ordering (for multiple media in one post)
    position = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<PostMedia(id={self.id}, post_id={self.post_id}, media_type='{self.media_type}')>"
