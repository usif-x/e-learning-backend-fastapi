# app/services/category_service.py

import math
from typing import Optional

from sqlalchemy.orm import Session, selectinload

from app.models.categories import Category
from app.schemas.categories import CategoryCreate, CategoryUpdate


class CategoryService:
    def __init__(self, db: Session):
        """
        The service is initialized with the database session from the endpoint.
        """
        self.db = db

    @staticmethod
    def _calculate_pagination(total: int, page: int, size: int):
        """Helper static method to calculate pagination details."""
        total_pages = math.ceil(total / size) if size > 0 else 0
        return {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
        }

    def get(self, category_id: int) -> Optional[Category]:
        """
        Retrieves a single category by its ID.
        """
        return (
            self.db.query(Category)
            .options(selectinload(Category.courses))
            .filter(Category.id == category_id)
            .first()
        )

    def get_all(self, page: int = 1, size: int = 20) -> (list[Category], dict):
        """
        Retrieves a paginated list of categories.
        """
        skip = (page - 1) * size
        query = self.db.query(Category).options(selectinload(Category.courses))

        total = query.count()
        categories = query.offset(skip).limit(size).all()

        pagination = self._calculate_pagination(total=total, page=page, size=size)
        return categories, pagination

    def create(self, category_in: CategoryCreate) -> Category:
        """
        Creates a new category.
        """
        db_category = Category(**category_in.model_dump())
        self.db.add(db_category)
        self.db.commit()
        self.db.refresh(db_category)
        return db_category

    def update(
        self, category_id: int, category_in: CategoryUpdate
    ) -> Optional[Category]:
        """
        Updates an existing category.
        """
        db_category = self.get(category_id=category_id)
        if not db_category:
            return None

        update_data = category_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_category, key, value)

        self.db.add(db_category)
        self.db.commit()
        self.db.refresh(db_category)
        return db_category

    def delete(self, category_id: int) -> Optional[Category]:
        """
        Deletes a category.
        """
        db_category = self.db.query(Category).filter(Category.id == category_id).first()
        if not db_category:
            return None

        self.db.delete(db_category)
        self.db.commit()
        return db_category
