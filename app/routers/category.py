# app/routers/category.py
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin, get_optional_user
from app.models.admin import Admin
from app.models.user import User
from app.schemas.category import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
)
from app.services.category import CategoryService

router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
    responses={404: {"description": "Not found"}},
)


# ==================== Category Endpoints ====================


@router.post("/", response_model=CategoryResponse, status_code=201)
def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Create a new category.
    Only admins can create categories.
    """
    service = CategoryService(db)
    return service.create_category(category_in, current_admin.id)


@router.get("/", response_model=CategoryListResponse)
def list_categories(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by name or description"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get list of categories with pagination.
    Available to all users (authenticated or not).
    """
    service = CategoryService(db)
    categories, pagination = service.get_categories(page, size, search)
    return {"categories": categories, **pagination}


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get a category by ID.
    Available to all users (authenticated or not).
    """
    service = CategoryService(db)
    category = service.get_category(category_id)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    return category


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Update a category.
    Only admins can update categories.
    """
    service = CategoryService(db)
    category = service.update_category(category_id, category_in, current_admin.id)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Delete a category.
    Only admins can delete categories.
    """
    service = CategoryService(db)
    service.delete_category(category_id, current_admin.id)
    return None


@router.post("/{category_id}/upload-image", response_model=CategoryResponse)
async def upload_category_image(
    category_id: int,
    image: UploadFile = File(..., description="Category image"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Upload a category image.
    Only admins can upload images.
    """
    service = CategoryService(db)
    category = await service.upload_category_image(category_id, image, current_admin.id)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    return category
