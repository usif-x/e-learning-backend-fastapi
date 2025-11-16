# app/models/course_enrollment.py
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CourseEnrollment(Base):
    """
    Tracks user course enrollments/subscriptions.
    Includes both free and paid course enrollments.
    """

    __tablename__ = "course_enrollments"

    id = Column(Integer, primary_key=True, index=True)

    # User and Course relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)

    # Enrollment details
    enrollment_type = Column(
        String(50), nullable=False, default="free"
    )  # 'free', 'paid', 'gift'
    price_paid = Column(
        Numeric(10, 2), nullable=True
    )  # Amount paid (NULL for free courses)

    # Payment reference (if applicable)
    payment_reference = Column(String(255), nullable=True)

    # Progress tracking
    completed_lectures = Column(Integer, default=0, nullable=False)
    total_lectures = Column(Integer, default=0, nullable=False)

    # Timestamps
    enrolled_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(
        DateTime(timezone=True), nullable=True
    )  # When user completed the course

    # Relationships
    user = relationship("User", backref="enrollments")
    course = relationship("Course", backref="enrollments")

    def __repr__(self):
        return f"<CourseEnrollment(id={self.id}, user_id={self.user_id}, course_id={self.course_id}, type={self.enrollment_type})>"
