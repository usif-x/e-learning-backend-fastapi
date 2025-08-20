# app/services/course_subscription_service.py

import math
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session, selectinload

from app.models.course_subscription import CourseSubscription
from app.models.courses import Course
from app.models.user import User
from app.schemas.course_subscription import CourseSubscriptionCreate


class CourseSubscriptionService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, subscription_in: CourseSubscriptionCreate) -> CourseSubscription:
        """
        Subscribes a user to a course.
        """
        # 1. Validate that the user exists
        user = self.db.query(User).filter(User.id == subscription_in.user_id).first()
        if not user:
            raise ValueError(f"User with id {subscription_in.user_id} not found.")

        # 2. Validate that the course exists and is sellable
        course = (
            self.db.query(Course).filter(Course.id == subscription_in.course_id).first()
        )
        if not course:
            raise ValueError(f"Course with id {subscription_in.course_id} not found.")
        if not course.is_sellable:
            raise ValueError(f"Course '{course.title}' is not available for purchase.")

        # 3. Check if the user is already subscribed
        existing_subscription = (
            self.db.query(CourseSubscription)
            .filter_by(user_id=user.id, course_id=course.id)
            .first()
        )
        if existing_subscription:
            raise ValueError("User is already subscribed to this course.")

        # 4. Determine price and handle payment
        price_to_pay = Decimal("0.00")  # Default to 0 for free courses

        # Only check for payment if the course is NOT free
        if not course.is_free:
            price_to_pay = (
                course.discount
                if course.has_discount and course.discount is not None
                else course.price
            )

            if subscription_in.payment_method == "wallet":
                if user.wallet_balance < price_to_pay:
                    raise ValueError("Insufficient funds in wallet.")
                user.wallet_balance -= price_to_pay
                self.db.add(user)

        # Create the subscription record regardless. This is important for tracking.
        db_subscription = CourseSubscription(
            user_id=user.id,
            course_id=course.id,
            price_paid=price_to_pay,  # Will be 0.00 for free courses
            payment_method=subscription_in.payment_method,
        )
        self.db.add(db_subscription)

        self.db.commit()
        self.db.refresh(db_subscription)

        return db_subscription
