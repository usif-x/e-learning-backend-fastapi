# app/services/course_service.py

import math
from typing import Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session, selectinload

from app.models.categories import Category
from app.models.course_subscription import CourseSubscription
from app.models.courses import Course
from app.models.lecture import Lecture
from app.models.user import User
from app.schemas.courses import CourseCreate, CourseUpdate
from app.utils.file_upload import file_upload_service


class CourseService:
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

    def get(self, course_id: int) -> Optional[Course]:
        """
        Retrieves a single course by its ID, eagerly loading relationships.
        """
        return (
            self.db.query(Course)
            .options(
                selectinload(Course.category),
                selectinload(Course.related_course),
            )
            .filter(Course.id == course_id)
            .first()
        )

    def get_all(
        self, page: int = 1, size: int = 20, current_user: Optional[User] = None
    ) -> tuple[list[Course], dict]:
        """
        Retrieves a paginated list of courses.
        If a user is provided, it efficiently annotates each course with subscription status.
        """
        skip = (page - 1) * size
        query = self.db.query(Course).options(selectinload(Course.category))

        total = query.count()
        courses = query.offset(skip).limit(size).all()

        subscribed_course_ids = set()
        if current_user and courses:
            course_ids_on_page = {c.id for c in courses}
            subscribed_course_ids = {
                sub.course_id
                for sub in self.db.query(CourseSubscription.course_id)
                .filter(
                    CourseSubscription.user_id == current_user.id,
                    CourseSubscription.course_id.in_(course_ids_on_page),
                )
                .all()
            }

        # --- THIS IS THE FIX ---
        # Annotate each course object with the subscription status
        for course in courses:
            # A user is subscribed if the course is free OR they have a subscription record.
            is_subscribed_status = course.is_free or (
                course.id in subscribed_course_ids
            )
            setattr(course, "is_subscribed", is_subscribed_status)

        pagination = self._calculate_pagination(total=total, page=page, size=size)
        return courses, pagination

    def get_course_by_id(self, course_id: int) -> Optional[Course]:
        """
        Retrieves a single course by its ID.
        """
        return self.db.query(Course).filter(Course.id == course_id).first()

    def create(self, course_in: CourseCreate) -> Course:
        """
        Creates a new course after validating foreign keys.
        """
        category = (
            self.db.query(Category).filter(Category.id == course_in.category_id).first()
        )
        if not category:
            raise ValueError(f"Category with id {course_in.category_id} not found.")

        if course_in.relation_course_id:
            related_course = (
                self.db.query(Course)
                .filter(Course.id == course_in.relation_course_id)
                .first()
            )
            if not related_course:
                raise ValueError(
                    f"Related course with id {course_in.relation_course_id} not found."
                )

        db_course = Course(**course_in.model_dump())
        self.db.add(db_course)
        self.db.commit()
        self.db.refresh(db_course)
        return db_course

    def update(self, course_id: int, course_in: CourseUpdate) -> Optional[Course]:
        """
        Updates an existing course after validating any changed foreign keys.
        """
        db_course = self.get(course_id=course_id)
        if not db_course:
            return None

        update_data = course_in.model_dump(exclude_unset=True)

        if "category_id" in update_data:
            category = (
                self.db.query(Category)
                .filter(Category.id == update_data["category_id"])
                .first()
            )
            if not category:
                raise ValueError(
                    f"Category with id {update_data['category_id']} not found."
                )

        for key, value in update_data.items():
            setattr(db_course, key, value)

        self.db.add(db_course)
        self.db.commit()
        self.db.refresh(db_course)
        return db_course

    def delete(self, course_id: int) -> Optional[Course]:
        """
        Deletes a course.
        """
        db_course = self.db.query(Course).filter(Course.id == course_id).first()
        if not db_course:
            return None

        self.db.delete(db_course)
        self.db.commit()
        return db_course

    def get_course_with_full_content(self, course_id: int) -> Optional[Course]:
        """
        Retrieves a single course and eagerly loads its entire content hierarchy:
        Course -> Lectures -> LectureContents.
        This is a performance-critical query.
        """
        return (
            self.db.query(Course)
            .options(
                # Eagerly load the 'lectures' collection, and FOR EACH lecture,
                # also eagerly load its 'contents' collection.
                selectinload(Course.lectures).selectinload(Lecture.contents)
            )
            .filter(Course.id == course_id)
            .first()
        )

    async def upload_course_image(
        self, course_id: int, image_file: UploadFile
    ) -> Optional[Course]:
        """
        Upload and attach an image to a course.

        Args:
            course_id: ID of the course
            image_file: The uploaded image file

        Returns:
            Updated course or None if course not found
        """
        # Get the course
        db_course = self.get(course_id=course_id)
        if not db_course:
            return None

        # Delete old image if exists
        if db_course.image:
            file_upload_service.delete_image(db_course.image)

        # Save new image
        uuid_filename, relative_path = await file_upload_service.save_image(
            image_file, folder="courses"
        )

        # Update course with new image path
        db_course.image = relative_path
        self.db.add(db_course)
        self.db.commit()
        self.db.refresh(db_course)

        return db_course

    async def delete_course_image(self, course_id: int) -> Optional[Course]:
        """
        Delete the image attached to a course.

        Args:
            course_id: ID of the course

        Returns:
            Updated course or None if course not found
        """
        db_course = self.get(course_id=course_id)
        if not db_course:
            return None

        # Delete the image file if exists
        if db_course.image:
            file_upload_service.delete_image(db_course.image)
            db_course.image = None
            self.db.add(db_course)
            self.db.commit()
            self.db.refresh(db_course)

        return db_course
