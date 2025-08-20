# app/schemas/course_prepaidable_user.py

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# --- Nested Schemas for Rich Responses ---
# Re-using the minimal schemas from the subscription file is a good idea,
# or you can define them here if you prefer separation.
class UserInPrepaidableResponse(BaseModel):
    id: int
    full_name: str
    telegram_id: str
    model_config = ConfigDict(from_attributes=True)


class CourseInPrepaidableResponse(BaseModel):
    id: int
    title: str
    model_config = ConfigDict(from_attributes=True)


# --- Main Schemas ---
class CoursePrepaidableUserCreate(BaseModel):
    user_id: int = Field(..., examples=[101])
    course_id: int = Field(..., examples=[42])


class CoursePrepaidableUserResponse(BaseModel):
    id: int
    created_at: datetime
    user: UserInPrepaidableResponse
    course: CourseInPrepaidableResponse

    model_config = ConfigDict(from_attributes=True)
