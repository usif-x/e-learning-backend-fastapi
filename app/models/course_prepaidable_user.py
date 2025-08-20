# app/models/course_prepaidable_user.py

from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CoursePrepaidableUser(Base):
    __tablename__ = "course_prepaidable_users"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys to link User and Course
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)

    # Timestamp for when the access was granted
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User")
    course = relationship("Course")
