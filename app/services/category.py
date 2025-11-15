# app/services/category.py
import math
from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.utils.file_upload import file_upload_service


class CategoryService:
    def __init__(self, db: Session):
        self.db = db

    def create_category(self, category_in: CategoryCreate, admin_id: int) -> Category:
        """Create a new category (admin only)"""
        # Check if category with same name exists
        existing = (
            self.db.query(Category).filter(Category.name == category_in.name).first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists",
            )

        category = Category(**category_in.model_dump())
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)

        return category

    def get_categories(
        self,
        page: int = 1,
        size: int = 20,
        search: Optional[str] = None,
    ) -> Tuple[List[Category], dict]:
        """Get list of categories with pagination"""
        query = self.db.query(Category)

        # Search by name or description
        if search:
            query = query.filter(
                or_(
                    Category.name.ilike(f"%{search}%"),
                    Category.description.ilike(f"%{search}%"),
                )
            )

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * size
        categories = (
            query.order_by(Category.name.asc()).offset(offset).limit(size).all()
        )

        # Pagination metadata
        total_pages = math.ceil(total / size) if size > 0 else 0
        pagination = {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
        }

        return categories, pagination

    def get_category(self, category_id: int) -> Optional[Category]:
        """Get a category by ID"""
        return self.db.query(Category).filter(Category.id == category_id).first()

    def update_category(
        self, category_id: int, category_in: CategoryUpdate, admin_id: int
    ) -> Optional[Category]:
        """Update a category (admin only)"""
        category = self.get_category(category_id)
        if not category:
            return None

        # Check if name is being changed and conflicts with another category
        if category_in.name and category_in.name != category.name:
            existing = (
                self.db.query(Category)
                .filter(
                    Category.name == category_in.name,
                    Category.id != category_id,
                )
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category with this name already exists",
                )

        # Update fields
        for field, value in category_in.model_dump(exclude_unset=True).items():
            setattr(category, field, value)

        self.db.commit()
        self.db.refresh(category)

        return category

    def delete_category(self, category_id: int, admin_id: int) -> bool:
        """Delete a category (admin only)"""
        category = self.get_category(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )

        # Delete image if exists
        if category.image:
            file_upload_service.delete_image(category.image)

        self.db.delete(category)
        self.db.commit()

        return True

    async def upload_category_image(
        self, category_id: int, image_file: UploadFile, admin_id: int
    ) -> Optional[Category]:
        """Upload category image (admin only)"""
        category = self.get_category(category_id)
        if not category:
            return None

        # Delete old image if exists
        if category.image:
            file_upload_service.delete_image(category.image)

        # Save new image
        uuid_filename, relative_path = await file_upload_service.save_image(
            image_file, folder="categories"
        )

        category.image = relative_path
        self.db.commit()
        self.db.refresh(category)

        return category
