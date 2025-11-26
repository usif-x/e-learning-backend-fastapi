from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.core.config import settings
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Authentication fields (no username - from telegram)
    email = Column(
        String(100), unique=True, index=True, nullable=True
    )  # Optional for phone-only users
    hashed_password = Column(
        String(255), nullable=True
    )  # Optional for phone-only users
    academic_id = Column(
        String(50), unique=True, index=True, nullable=True
    )  # For academic registration/login

    # Profile information (from Telegram + optional)
    full_name = Column(
        String(100), nullable=False
    )  # From telegram first_name + last_name
    phone_number = Column(String(20), unique=True, nullable=True)
    parent_phone_number = Column(String(20), nullable=True)
    profile_picture = Column(Text, nullable=True)  # From telegram photo_url or custom

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=settings.verify_user_model, nullable=False)
    status = Column(
        String(20), default=settings.authorization_default_role, nullable=False
    )  # student, teacher, admin

    # Telegram integration (required)
    telegram_id = Column(
        String(50), unique=True, nullable=False, index=True
    )  # Primary identifier
    telegram_username = Column(
        String(50), unique=True, nullable=True
    )  # @username from telegram
    telegram_first_name = Column(String(50), nullable=False)  # From telegram
    telegram_last_name = Column(String(50), nullable=True)  # From telegram
    telegram_hash = Column(String(255), nullable=True)  # Store telegram auth hash
    telegram_verified = Column(Boolean, default=False, nullable=False)

    sex = Column(String(10), nullable=True, server_default="Male")  #

    reset_code = Column(String(6), nullable=True)  # 6-digit verification code
    reset_code_expires_at = Column(DateTime(timezone=True), nullable=True)

    wallet_balance = Column(Numeric(10, 2), nullable=False, default=0)

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
    last_login = Column(DateTime(timezone=True), nullable=True)
    telegram_verified_at = Column(DateTime(timezone=True), nullable=True)

    class Config:
        from_attributes = True

    @property
    def display_name(self) -> str:
        """Get display name from telegram data"""
        if self.telegram_last_name:
            return f"{self.telegram_first_name} {self.telegram_last_name}"
        return self.telegram_first_name

    @property
    def identifier(self) -> str:
        """Get primary identifier (telegram_username or telegram_id)"""
        return self.telegram_username or f"user_{self.telegram_id}"

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id='{self.telegram_id}', name='{self.display_name}')>"
