# app/schemas/course_subscription.py

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Nested Schemas for Rich Responses ---
# Minimal representation of a User in a subscription response
class UserInSubscriptionResponse(BaseModel):
    id: int
    full_name: str
    telegram_id: str

    model_config = ConfigDict(from_attributes=True)


# Minimal representation of a Course in a subscription response
class CourseInSubscriptionResponse(BaseModel):
    id: int
    title: str

    model_config = ConfigDict(from_attributes=True)


# --- Main Schemas ---


class CourseSubscriptionBase(BaseModel):
    user_id: int = Field(..., examples=[101])
    course_id: int = Field(..., examples=[42])


class CourseSubscriptionCreate(CourseSubscriptionBase):
    payment_method: str = Field("wallet", examples=["wallet", "stripe"])


class CourseSubscriptionResponse(CourseSubscriptionBase):
    id: int
    price_paid: Decimal
    payment_method: str
    is_active: bool
    created_at: datetime

    # Include the nested objects for a complete response
    user: UserInSubscriptionResponse
    course: CourseInSubscriptionResponse

    model_config = ConfigDict(from_attributes=True)


class CourseSubscriptionListResponse(BaseModel):
    subscriptions: list[CourseSubscriptionResponse]
    total: int
    page: int
    size: int
    total_pages: int
