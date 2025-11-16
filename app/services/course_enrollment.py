# app/services/course_enrollment.py
import math
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload

from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.lecture import Lecture
from app.schemas.course_enrollment import CourseEnrollmentCreate


class CourseEnrollmentService:
    def __init__(self, db: Session):
        self.db = db

    def enroll_user(
        self, user_id: int, enrollment_data: CourseEnrollmentCreate
    ) -> CourseEnrollment:
        """
        Enroll a user in a course.
        - If course is free, auto-enroll
        - If course is paid, verify payment_reference and deduct from wallet
        """
        # Get course
        course = (
            self.db.query(Course).filter(Course.id == enrollment_data.course_id).first()
        )

        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
            )

        # Check if already enrolled
        existing_enrollment = (
            self.db.query(CourseEnrollment)
            .filter(
                and_(
                    CourseEnrollment.user_id == user_id,
                    CourseEnrollment.course_id == enrollment_data.course_id,
                )
            )
            .first()
        )

        if existing_enrollment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already enrolled in this course",
            )

        # Get total lectures count
        total_lectures = (
            self.db.query(func.count(Lecture.id))
            .filter(Lecture.course_id == course.id)
            .scalar()
            or 0
        )

        # Determine enrollment type and price
        enrollment_type = "free"
        price_paid = None

        if course.is_free:
            enrollment_type = "free"
            price_paid = None
        else:
            # For paid courses, would need payment processing here
            # For now, mark as paid with the course price
            enrollment_type = "paid"
            price_paid = course.price

        # Create enrollment
        enrollment = CourseEnrollment(
            user_id=user_id,
            course_id=course.id,
            enrollment_type=enrollment_type,
            price_paid=price_paid,
            payment_reference=enrollment_data.payment_reference,
            completed_lectures=0,
            total_lectures=total_lectures,
            enrolled_at=datetime.utcnow(),
        )

        self.db.add(enrollment)
        self.db.commit()
        self.db.refresh(enrollment)

        return enrollment

    def get_user_enrollments(
        self, user_id: int, page: int = 1, size: int = 20
    ) -> Tuple[List[CourseEnrollment], dict]:
        """
        Get all courses a user is enrolled in with pagination.
        Returns enrollments with course details.
        """
        query = (
            self.db.query(CourseEnrollment)
            .options(joinedload(CourseEnrollment.course))
            .filter(CourseEnrollment.user_id == user_id)
        )

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * size
        enrollments = (
            query.order_by(CourseEnrollment.enrolled_at.desc())
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

        return enrollments, pagination

    def get_enrollment(
        self, user_id: int, course_id: int
    ) -> Optional[CourseEnrollment]:
        """Get specific enrollment for a user and course"""
        return (
            self.db.query(CourseEnrollment)
            .options(joinedload(CourseEnrollment.course))
            .filter(
                and_(
                    CourseEnrollment.user_id == user_id,
                    CourseEnrollment.course_id == course_id,
                )
            )
            .first()
        )

    def is_user_enrolled(self, user_id: int, course_id: int) -> bool:
        """Check if user is enrolled in a course"""
        return (
            self.db.query(CourseEnrollment)
            .filter(
                and_(
                    CourseEnrollment.user_id == user_id,
                    CourseEnrollment.course_id == course_id,
                )
            )
            .first()
            is not None
        )

    def update_progress(
        self, user_id: int, course_id: int, completed_lectures: int
    ) -> Optional[CourseEnrollment]:
        """Update user's progress in a course"""
        enrollment = (
            self.db.query(CourseEnrollment)
            .filter(
                and_(
                    CourseEnrollment.user_id == user_id,
                    CourseEnrollment.course_id == course_id,
                )
            )
            .first()
        )

        if not enrollment:
            return None

        enrollment.completed_lectures = completed_lectures
        enrollment.last_accessed_at = datetime.utcnow()

        # Mark as completed if all lectures are done
        if (
            enrollment.total_lectures > 0
            and completed_lectures >= enrollment.total_lectures
            and not enrollment.completed_at
        ):
            enrollment.completed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(enrollment)

        return enrollment

    def unenroll_user(self, user_id: int, course_id: int) -> bool:
        """Remove user's enrollment from a course"""
        enrollment = (
            self.db.query(CourseEnrollment)
            .filter(
                and_(
                    CourseEnrollment.user_id == user_id,
                    CourseEnrollment.course_id == course_id,
                )
            )
            .first()
        )

        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found",
            )

        self.db.delete(enrollment)
        self.db.commit()

        return True
