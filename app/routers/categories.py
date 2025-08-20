# app/routers/categories.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db

# Direct imports from the specific schema file
from app.schemas.categories import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
)
from app.services.categories import CategoryService

router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=CategoryResponse, status_code=201)
def create_category(category_in: CategoryCreate, db: Session = Depends(get_db)):
    """
    Create a new category.
    """
    service = CategoryService(db)
    return service.create(category_in=category_in)


@router.get("/{category_id}", response_model=CategoryResponse)
def read_category(category_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a single category by its ID.
    """
    service = CategoryService(db)
    db_category = service.get(category_id=category_id)
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return db_category


@router.get("/", response_model=CategoryListResponse)
def read_categories(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """
    Retrieve a paginated list of categories.
    """
    service = CategoryService(db)
    categories, pagination = service.get_all(page=page, size=size)
    return {"categories": categories, **pagination}


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int, category_in: CategoryUpdate, db: Session = Depends(get_db)
):
    """
    Update an existing category.
    """
    service = CategoryService(db)
    updated_category = service.update(category_id=category_id, category_in=category_in)
    if updated_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return updated_category


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """
    Delete a category.
    """
    service = CategoryService(db)
    deleted_category = service.delete(category_id=category_id)
    if deleted_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return None
