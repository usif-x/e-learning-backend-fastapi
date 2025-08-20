# app/schemas/lecture.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .lecture_content import LectureContentResponse  # <-- Import nested schema


class LectureBase(BaseModel):
    title: str
    description: str | None = None
    position: int


class LectureCreate(LectureBase):
    course_id: int


class LectureUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    position: int | None = None


class LectureResponse(LectureBase):
    id: int
    created_at: datetime
    updated_at: datetime
    contents: list[LectureContentResponse] = []  # <-- The nested list
    model_config = ConfigDict(from_attributes=True)
