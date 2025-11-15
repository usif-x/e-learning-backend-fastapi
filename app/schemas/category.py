# app/schemas/category.py
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

# ==================== Category Schemas ====================


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    image: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    image: Optional[str] = None


class CategoryResponse(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class CategoryListResponse(BaseModel):
    categories: List[CategoryResponse]
    total: int
    page: int
    size: int
    total_pages: int
