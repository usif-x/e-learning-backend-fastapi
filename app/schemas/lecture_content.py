# app/schemas/lecture_content.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LectureContentBase(BaseModel):
    title: str
    description: str | None = None
    content_type: str
    content_source: str
    position: int
    is_opened: bool = True
    depends_on_content_id: int | None = None


class LectureContentCreate(LectureContentBase):
    lecture_id: int


class LectureContentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    content_type: str | None = None
    content_source: str | None = None
    position: int | None = None
    is_opened: bool | None = None
    depends_on_content_id: int | None = None


class LectureContentResponse(LectureContentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
