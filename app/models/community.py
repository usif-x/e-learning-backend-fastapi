# app/models/community.py
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Community(Base):
    __tablename__ = "communities"

    id = Column(Integer, primary_key=True, index=True)

    # Basic Info
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    image = Column(Text, nullable=True)  # Community profile image

    # Privacy Settings
    is_public = Column(Boolean, default=True, nullable=False)
    invite_code = Column(
        String(50), unique=True, nullable=True, index=True
    )  # For private communities

    # Community Settings
    is_active = Column(Boolean, default=True, nullable=False)
    allow_member_posts = Column(Boolean, default=True, nullable=False)
    require_approval = Column(
        Boolean, default=False, nullable=False
    )  # For join requests

    # Statistics (can be computed but useful for performance)
    members_count = Column(Integer, default=0, nullable=False)
    posts_count = Column(Integer, default=0, nullable=False)

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
        return (
            f"<Community(id={self.id}, name='{self.name}', is_public={self.is_public})>"
        )
