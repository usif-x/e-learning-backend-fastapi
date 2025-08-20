# app/services/user_service.py

from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.models.course_subscription import CourseSubscription
from app.models.courses import Course
from app.models.user import User


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_user(self, user_id: int) -> Optional[User]:
        """
        Retrieves a single user by their ID.
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def get_subscribed_courses(self, user_id: int) -> Optional[List[Course]]:
        """
        Retrieves a list of ALL courses a user has access to.
        This includes:
        1. Courses they have an active subscription record for.
        2. All courses that are marked as free.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        # Get IDs of courses the user is explicitly subscribed to
        subscribed_course_ids = [
            sub.course_id
            for sub in self.db.query(CourseSubscription.course_id).filter(
                CourseSubscription.user_id == user_id
            )
        ]

        # Query for all courses that are EITHER in the subscribed list OR are free
        accessible_courses = (
            self.db.query(Course)
            .filter(or_(Course.id.in_(subscribed_course_ids), Course.is_free == True))
            .all()
        )

        return accessible_courses
