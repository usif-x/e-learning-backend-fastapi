# app/routers/course_subscriptions.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.course_subscription import (
    CourseSubscriptionCreate,
    CourseSubscriptionResponse,
)
from app.services.course_subscription import CourseSubscriptionService

router = APIRouter(
    prefix="/course-subscriptions",
    tags=["Course Subscriptions"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=CourseSubscriptionResponse, status_code=201)
def subscribe_user_to_course(
    subscription_in: CourseSubscriptionCreate, db: Session = Depends(get_db)
):
    """
    Create a new subscription for a user to a course.

    Handles validation, payment from wallet, and record creation.
    """
    service = CourseSubscriptionService(db)
    try:
        new_subscription = service.create(subscription_in=subscription_in)
        return new_subscription
    except ValueError as e:
        # Catch validation errors from the service and return a 400 Bad Request
        raise HTTPException(status_code=400, detail=str(e))
