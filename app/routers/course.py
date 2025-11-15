# app/routers/course.py
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin, get_optional_user
from app.models.admin import Admin
from app.models.user import User
from app.schemas.course import (
    CourseCreate,
    CourseListResponse,
    CourseResponse,
    CourseUpdate,
)
from app.services.course import CourseService

router = APIRouter(
    prefix="/courses",
    tags=["Courses"],
    responses={404: {"description": "Not found"}},
)


# ==================== Course Endpoints ====================


@router.post("/", response_model=CourseResponse, status_code=201)
def create_course(
    course_in: CourseCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Create a new course.
    Only admins can create courses.
    """
    service = CourseService(db)
    return service.create_course(course_in, current_admin.id)


@router.get("/", response_model=CourseListResponse)
def list_courses(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    is_pinned: Optional[bool] = Query(None, description="Filter by pinned status"),
    sellable: Optional[bool] = Query(None, description="Filter by sellable status"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get list of courses with pagination and filters.
    Available to all users (authenticated or not).
    """
    service = CourseService(db)
    courses, pagination = service.get_courses(
        page=page,
        size=size,
        category_id=category_id,
        search=search,
        is_pinned=is_pinned,
        sellable=sellable,
    )
    return {"courses": courses, **pagination}


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get a course by ID.
    Available to all users (authenticated or not).
    """
    service = CourseService(db)
    course = service.get_course(course_id)

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    return course


@router.patch("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int,
    course_in: CourseUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Update a course.
    Only admins can update courses.
    """
    service = CourseService(db)
    course = service.update_course(course_id, course_in, current_admin.id)

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    return course


@router.delete("/{course_id}", status_code=204)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Delete a course.
    Only admins can delete courses.
    """
    service = CourseService(db)
    service.delete_course(course_id, current_admin.id)
    return None


@router.post("/{course_id}/upload-image", response_model=CourseResponse)
async def upload_course_image(
    course_id: int,
    image: UploadFile = File(..., description="Course image"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Upload a course image.
    Only admins can upload images.
    """
    service = CourseService(db)
    course = await service.upload_course_image(course_id, image, current_admin.id)

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    return course
