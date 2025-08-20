# app/schemas/category.py

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Nested Schema for Relationships ---
# A minimal view of a Course for when it's part of a Category response.
class CourseInCategoryResponse(BaseModel):
    id: int
    title: str
    price: Decimal
    is_pinned: bool

    model_config = ConfigDict(from_attributes=True)


# --- Main Category Schemas ---


class CategoryBase(BaseModel):
    title: str = Field(..., max_length=100, examples=["Programming"])
    description: Optional[str] = Field(
        None, examples=["Courses about software development."]
    )
    has_image: bool = False
    image: Optional[str] = Field(
        None, examples=["https://example.com/images/programming.jpg"]
    )


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    has_image: Optional[bool] = None
    image: Optional[str] = None


class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    # The relationship to Courses will be a list of the minimal Course schema
    courses: list[CourseInCategoryResponse] = []

    model_config = ConfigDict(
        from_attributes=True,
    )

    # In your SQLAlchemy query, you might need to do something like:
    # category = db.query(models.Category).options(selectinload(models.Category.courses)).first()
    # Pydantic will then correctly populate the 'courses' list.
    # The `lazy="dynamic"` in your model means `category.courses` is a query;
    # you would need to execute it (`category.courses.all()`) before passing it
    # to Pydantic, or change lazy loading strategy to "selectin" or "joined".


class CategoryListResponse(BaseModel):
    categories: list[CategoryResponse]
    total: int
    page: int
    size: int
    total_pages: int

    model_config = ConfigDict(
        from_attributes=True,
    )
