# app/schemas/course_enrollment.py
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

# ==================== Course Enrollment Schemas ====================


class CourseEnrollmentBase(BaseModel):
    """Base schema for course enrollment"""

    course_id: int = Field(..., description="Course ID")
    enrollment_type: str = Field(
        default="free", description="Enrollment type (free, paid, gift)"
    )
    price_paid: Optional[Decimal] = Field(
        None, description="Amount paid for enrollment"
    )
    payment_reference: Optional[str] = Field(None, description="Payment reference ID")


class CourseEnrollmentCreate(BaseModel):
    """Schema for enrolling in a course"""

    course_id: int = Field(..., description="Course ID to enroll in")
    payment_reference: Optional[str] = Field(
        None, description="Payment reference for paid courses"
    )


class CourseEnrollmentResponse(BaseModel):
    """Schema for course enrollment response"""

    id: int
    user_id: int
    course_id: int
    enrollment_type: str
    price_paid: Optional[Decimal]
    payment_reference: Optional[str]
    completed_lectures: int
    total_lectures: int
    enrolled_at: datetime
    last_accessed_at: Optional[datetime]
    completed_at: Optional[datetime]

    # Include course details
    course_name: Optional[str] = None
    course_image: Optional[str] = None
    course_price: Optional[Decimal] = None

    class Config:
        from_attributes = True


class EnrolledCourseResponse(BaseModel):
    """Detailed response for enrolled courses with progress"""

    id: int
    user_id: int
    course_id: int
    enrollment_type: str
    price_paid: Optional[Decimal]
    completed_lectures: int
    total_lectures: int
    progress_percentage: float = Field(0.0, description="Course completion percentage")
    enrolled_at: datetime
    last_accessed_at: Optional[datetime]
    completed_at: Optional[datetime]

    # Course details
    course_name: str
    course_description: Optional[str]
    course_image: Optional[str]
    course_price: Decimal
    course_is_free: bool

    class Config:
        from_attributes = True


class EnrolledCoursesListResponse(BaseModel):
    """Response for list of enrolled courses with pagination"""

    enrollments: list[EnrolledCourseResponse]
    total: int
    page: int
    size: int
    total_pages: int
