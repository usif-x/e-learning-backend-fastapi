# app/schemas/user.py

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    full_name: str
    telegram_id: str
    telegram_username: Optional[str] = None
    phone_number: Optional[str] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    status: str
    wallet_balance: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(BaseModel):
    """Detailed user profile for current user"""

    id: int
    full_name: str
    email: Optional[str]
    phone_number: Optional[str]
    parent_phone_number: Optional[str]
    profile_picture: Optional[str]
    telegram_id: str
    telegram_username: Optional[str]
    telegram_first_name: str
    telegram_last_name: Optional[str]
    is_active: bool
    is_verified: bool
    status: str
    wallet_balance: Decimal
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]
    telegram_verified_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class UpdatePasswordRequest(BaseModel):
    """Request to update user password"""

    current_password: str
    new_password: str
    confirm_password: str


class ForgotPasswordRequest(BaseModel):
    """Request to initiate password reset"""

    phone_number: str  # User's phone number


class VerifyResetCodeRequest(BaseModel):
    """Request to verify reset code"""

    phone_number: str  # User's phone number
    code: str  # 6-digit verification code


class ResetPasswordRequest(BaseModel):
    """Request to reset password with verification code"""

    phone_number: str  # User's phone number
    code: str  # 6-digit verification code
    new_password: str
    confirm_password: str
