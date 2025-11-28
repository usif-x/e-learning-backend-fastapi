from sqlalchemy import Column, Date, DateTime, Integer, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class UserDailyUsage(Base):
    """Track user daily activity in minutes"""

    __tablename__ = "user_daily_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    minutes_spent = Column(Integer, default=0, nullable=False)
    last_ping = Column(DateTime(timezone=True), nullable=True)

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

    # Ensure one record per user per day
    __table_args__ = (UniqueConstraint("user_id", "date", name="uix_user_date"),)

    def __repr__(self):
        return f"<UserDailyUsage(user_id={self.user_id}, date={self.date}, minutes={self.minutes_spent})>"
