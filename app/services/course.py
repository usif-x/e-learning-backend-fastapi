# app/services/course.py
import math
from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.course import Course
from app.schemas.course import CourseCreate, CourseUpdate
from app.utils.file_upload import file_upload_service


class CourseService:
    def __init__(self, db: Session):
        self.db = db

    def create_course(self, course_in: CourseCreate, admin_id: int) -> Course:
        """Create a new course (admin only)"""
        course = Course(**course_in.model_dump())

        self.db.add(course)
        self.db.commit()
        self.db.refresh(course)

        return course

    def get_course(self, course_id: int) -> Optional[Course]:
        """Get a course by ID"""
        return self.db.query(Course).filter(Course.id == course_id).first()

    def get_courses(
        self,
        page: int = 1,
        size: int = 20,
        category_id: Optional[int] = None,
        search: Optional[str] = None,
        is_pinned: Optional[bool] = None,
        sellable: Optional[bool] = None,
    ) -> Tuple[List[Course], dict]:
        """Get list of courses with pagination and filters"""
        query = self.db.query(Course)

        # Filter by category
        if category_id is not None:
            query = query.filter(Course.category_id == category_id)

        # Filter by sellable status
        if sellable is not None:
            query = query.filter(Course.sellable == sellable)

        # Filter by pinned status
        if is_pinned is not None:
            query = query.filter(Course.is_pinned == is_pinned)

        # Search by name or description
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Course.name.ilike(search_pattern))
                | (Course.description.ilike(search_pattern))
            )

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * size
        courses = (
            query.order_by(Course.is_pinned.desc(), Course.created_at.desc())
            .offset(offset)
            .limit(size)
            .all()
        )

        # Pagination metadata
        total_pages = math.ceil(total / size) if size > 0 else 0
        pagination = {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
        }

        return courses, pagination

    def update_course(
        self, course_id: int, course_in: CourseUpdate, admin_id: int
    ) -> Optional[Course]:
        """Update a course (admin only)"""
        course = self.db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return None

        # Update fields
        for field, value in course_in.model_dump(exclude_unset=True).items():
            setattr(course, field, value)

        self.db.commit()
        self.db.refresh(course)

        return course

    def delete_course(self, course_id: int, admin_id: int) -> bool:
        """Delete a course (admin only)"""
        course = self.db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # Delete course image if exists
        if course.image:
            file_upload_service.delete_image(course.image)

        self.db.delete(course)
        self.db.commit()

        return True

    async def upload_course_image(
        self, course_id: int, image_file: UploadFile, admin_id: int
    ) -> Optional[Course]:
        """Upload course image (admin only)"""
        course = self.db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return None

        # Delete old image if exists
        if course.image:
            file_upload_service.delete_image(course.image)

        # Save new image
        uuid_filename, relative_path = await file_upload_service.save_image(
            image_file, folder="courses"
        )

        course.image = relative_path
        self.db.commit()
        self.db.refresh(course)

        return course
