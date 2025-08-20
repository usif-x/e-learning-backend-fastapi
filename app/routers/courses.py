# app/routers/courses.py

from typing import Union

from fastapi import (  # Add Union and Security
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Security,
)
from fastapi.security import HTTPAuthorizationCredentials  # For type hinting
from sqlalchemy.orm import Session

from app.core.database import get_db

# Import your dependency
# Assuming it's in a file like app/api/dependencies.py
from app.core.dependencies import (
    get_enrolled_course_for_current_user,
    get_optional_user,
    security,
)
from app.models.course_subscription import CourseSubscription
from app.models.courses import Course
from app.models.user import User  # Import the User model

# Direct imports from the specific schema file
from app.schemas.courses import (
    CourseCreate,
    CourseListResponse,
    CourseResponse,
    CourseUpdate,
    CourseWithContentResponse,
)
from app.services.courses import CourseService

router = APIRouter(
    prefix="/courses",
    tags=["Courses"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=CourseResponse, status_code=201)
def create_course(course_in: CourseCreate, db: Session = Depends(get_db)):
    """
    Create a new course.
    """
    service = CourseService(db)
    try:
        new_course = service.create(course_in=course_in)
        return new_course
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=CourseListResponse)
def read_courses(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """
    Retrieve a paginated list of courses.
    """
    service = CourseService(db)
    courses, pagination = service.get_all(page=page, size=size)
    return {"courses": courses, **pagination}


@router.patch("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int, course_in: CourseUpdate, db: Session = Depends(get_db)
):
    """
    Update an existing course.
    """
    service = CourseService(db)
    try:
        updated_course = service.update(course_id=course_id, course_in=course_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if updated_course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return updated_course


@router.delete("/{course_id}", status_code=204)
def delete_course(course_id: int, db: Session = Depends(get_db)):
    """
    Delete a course.
    """
    service = CourseService(db)
    deleted_course = service.delete(course_id=course_id)
    if deleted_course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return None


@router.get("/{course_id}/content", response_model=CourseWithContentResponse)
async def get_full_course_content(
    course_id: int,  # We still need the ID to pass to the service
    # The dependency already checks enrollment and returns a basic course object
    enrolled_course: Course = Depends(get_enrolled_course_for_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the complete content structure (lectures and lecture content) for a course.
    This endpoint is protected and only accessible to enrolled users.
    """
    service = CourseService(db)
    # Fetch the course again, but this time with the full content hierarchy loaded
    course_with_content = service.get_course_with_full_content(course_id=course_id)

    # We don't need to check if it exists, because the dependency already did.
    return course_with_content
