# app/schemas/course.py

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .lecture import LectureResponse


# --- Nested Schemas for Relationships ---
# This is a minimal schema to represent a Category when it's nested inside a Course.
# This prevents circular dependencies where Course needs Category and Category needs Course.
class CategoryInCourseResponse(BaseModel):
    id: int
    title: str

    model_config = ConfigDict(from_attributes=True)


# --- Main Course Schemas ---


class CourseBase(BaseModel):
    title: str = Field(..., max_length=100, examples=["Advanced Python Programming"])
    description: Optional[str] = Field(
        None, examples=["Dive deep into Python concepts."]
    )
    image: Optional[str] = Field(
        None, examples=["https://example.com/images/python.jpg"]
    )
    price: Decimal = Field(..., max_digits=10, decimal_places=2, examples=[99.99])

    # Foreign Keys for Create/Update
    category_id: int = Field(..., examples=[1])
    relation_course_id: Optional[int] = Field(None, examples=[5])

    # Boolean flags
    has_discount: bool = False
    is_sellable: bool = True
    is_pinned: bool = False
    has_relation_with_another_course: bool = False
    has_certificate: bool = False
    is_azhar: bool = False
    is_free: bool = False
    prepaidable: bool = False
    visible_alone: bool = False
    study_year: int = Field(1, examples=[3])

    # Optional discount
    discount: Optional[Decimal] = Field(
        None, max_digits=10, decimal_places=2, examples=[79.99]
    )


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    # All fields are optional for PATCH requests
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    image: Optional[str] = None
    price: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)
    category_id: Optional[int] = None
    relation_course_id: Optional[int] = None
    has_discount: Optional[bool] = None
    is_sellable: Optional[bool] = None
    is_pinned: Optional[bool] = None
    has_relation_with_another_course: Optional[bool] = None
    has_certificate: Optional[bool] = None
    is_azhar: Optional[bool] = None
    is_free: Optional[bool] = None
    prepaidable: Optional[bool] = None
    visible_alone: Optional[bool] = None
    study_year: Optional[int] = None
    discount: Optional[Decimal] = Field(None, max_digits=10, decimal_places=2)


class CourseResponse(CourseBase):
    id: int
    created_at: datetime
    updated_at: datetime

    # The 'category_id' from base is replaced by the full 'category' object
    category: CategoryInCourseResponse

    # Self-referential relationship:
    # Use a forward reference (string name) to the model itself.
    # This will be resolved later.
    related_course: Optional["CourseResponse"] = None

    has_discount: bool = False
    is_sellable: bool = True
    is_pinned: bool = False
    has_relation_with_another_course: bool = False
    has_certificate: bool = False
    is_azhar: bool = False
    is_free: bool = False
    prepaidable: bool = False
    is_subscribed: bool = False
    visible_alone: bool = False
    study_year: int = Field(1, examples=[3])

    model_config = ConfigDict(
        from_attributes=True,  # Enable ORM mode
    )


class CourseListResponse(BaseModel):
    courses: list[CourseResponse]
    total: int
    page: int
    size: int
    total_pages: int

    model_config = ConfigDict(
        from_attributes=True,
    )


class CourseWithContentResponse(CourseResponse):
    lectures: list[LectureResponse] = []
