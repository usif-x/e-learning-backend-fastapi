from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class QuizSourceBase(BaseModel):
    filename: str
    file_path: str


class QuizSourceCreate(BaseModel):
    filename: str
    file_path: str


class QuizSourceResponse(QuizSourceBase):
    id: int
    uploaded_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class QuizSourceListResponse(BaseModel):
    sources: list[QuizSourceResponse]
    total: int
    page: int
    size: int
    total_pages: int
