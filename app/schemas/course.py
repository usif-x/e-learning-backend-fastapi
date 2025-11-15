# app/schemas/course.py
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

# ==================== Course Schemas ====================


class CourseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    image: Optional[str] = None
    price: float = Field(..., ge=0)
    price_before_discount: Optional[float] = Field(None, ge=0)
    category_id: Optional[int] = None
    is_free: bool = False
    is_pinned: bool = False
    prepaidable: bool = False
    is_couponable: bool = True
    sellable: bool = True


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    image: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    price_before_discount: Optional[float] = Field(None, ge=0)
    category_id: Optional[int] = None
    is_free: Optional[bool] = None
    is_pinned: Optional[bool] = None
    prepaidable: Optional[bool] = None
    is_couponable: Optional[bool] = None
    sellable: Optional[bool] = None


class CourseResponse(CourseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class CourseListResponse(BaseModel):
    courses: List[CourseResponse]
    total: int
    page: int
    size: int
    total_pages: int
