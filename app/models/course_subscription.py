from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.sql import func

from app.core.database import Base


class CourseSubscription(Base):
    __tablename__ = "course_subscriptions"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys to link User and Course
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)

    # Metadata about the subscription
    price_paid = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(
        String(50), nullable=False, default="wallet"
    )  # e.g., "wallet", "stripe"
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
