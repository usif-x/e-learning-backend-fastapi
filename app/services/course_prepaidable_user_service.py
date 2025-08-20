# app/services/course_prepaidable_user_service.py

from typing import Optional

from sqlalchemy.orm import Session

from app.models.course_prepaidable_user import CoursePrepaidableUser
from app.models.courses import Course
from app.models.user import User
from app.schemas.course_prepaidable_user import CoursePrepaidableUserCreate


class CoursePrepaidableUserService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data_in: CoursePrepaidableUserCreate) -> CoursePrepaidableUser:
        """
        Grants a user prepaidable access to a course.
        """
        # 1. Validate that the user exists
        user = self.db.query(User).filter(User.id == data_in.user_id).first()
        if not user:
            raise ValueError(f"User with id {data_in.user_id} not found.")

        # 2. Validate that the course exists
        course = self.db.query(Course).filter(Course.id == data_in.course_id).first()
        if not course:
            raise ValueError(f"Course with id {data_in.course_id} not found.")

        # 3. Check if the permission already exists
        existing_permission = (
            self.db.query(CoursePrepaidableUser)
            .filter_by(user_id=user.id, course_id=course.id)
            .first()
        )
        if existing_permission:
            raise ValueError("User already has prepaidable access to this course.")

        # 4. Create the permission record
        db_permission = CoursePrepaidableUser(
            user_id=user.id,
            course_id=course.id,
        )
        self.db.add(db_permission)
        self.db.commit()
        self.db.refresh(db_permission)

        return self.get(db_permission.id)

    def delete(self, user_id: int, course_id: int) -> Optional[CoursePrepaidableUser]:
        """
        Revokes a user's prepaidable access to a course.
        """
        permission = (
            self.db.query(CoursePrepaidableUser)
            .filter_by(user_id=user_id, course_id=course_id)
            .first()
        )
        if not permission:
            return None  # Not found

        self.db.delete(permission)
        self.db.commit()
        return permission
