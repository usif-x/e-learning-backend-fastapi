# app/routers/course_prepaidable_users.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.course_prepaidable_user import (
    CoursePrepaidableUserCreate,
    CoursePrepaidableUserResponse,
)
from app.services.course_prepaidable_user_service import CoursePrepaidableUserService

router = APIRouter(
    prefix="/course-prepaidable-users",
    tags=["Course Prepaidable Users"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=CoursePrepaidableUserResponse, status_code=201)
def grant_prepaidable_access(
    data_in: CoursePrepaidableUserCreate, db: Session = Depends(get_db)
):
    """
    Grant a user prepaidable access to a specific course.
    """
    service = CoursePrepaidableUserService(db)
    try:
        new_permission = service.create(data_in=data_in)
        return new_permission
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/", status_code=204)
def revoke_prepaidable_access(
    user_id: int = Query(..., description="ID of the user"),
    course_id: int = Query(..., description="ID of the course"),
    db: Session = Depends(get_db),
):
    """
    Revoke a user's prepaidable access to a course.
    """
    service = CoursePrepaidableUserService(db)
    deleted_permission = service.delete(user_id=user_id, course_id=course_id)

    if deleted_permission is None:
        raise HTTPException(
            status_code=404, detail="Prepaidable access permission not found."
        )

    return None  # Returns 204 No Content
