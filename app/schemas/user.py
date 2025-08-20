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
