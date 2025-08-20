# app/routers/users.py

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

# Import the specific schemas we need
from app.schemas.courses import CourseResponse
from app.schemas.user import UserResponse
from app.services.user import UserService

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a single user by their ID.
    """
    service = UserService(db)
    db_user = service.get_user(user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.get("/{user_id}/subscribed-courses", response_model=List[CourseResponse])
def read_user_subscribed_courses(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a list of all courses a user is subscribed to.
    """
    service = UserService(db)

    # The service method returns either a list of courses or None
    subscribed_courses = service.get_subscribed_courses(user_id=user_id)

    if subscribed_courses is None:
        # This means the user with the given user_id was not found
        raise HTTPException(status_code=404, detail="User not found")

    # FastAPI will automatically convert the list of Course ORM models
    # into a JSON list of CourseResponse objects.
    return subscribed_courses
