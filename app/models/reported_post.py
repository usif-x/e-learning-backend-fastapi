# app/models/reported_post.py
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class ReportedPost(Base):
    __tablename__ = "reported_posts"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    reporter_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )  # User who reported
    reviewed_by = Column(
        Integer, ForeignKey("admins.id"), nullable=True, index=True
    )  # Admin who reviewed

    # Report Details
    reason = Column(Text, nullable=False)  # Why the post was reported
    report_status = Column(
        String(20), default="pending", nullable=False, index=True
    )  # pending, passed, deleted

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<ReportedPost(id={self.id}, post_id={self.post_id}, status='{self.report_status}')>"
