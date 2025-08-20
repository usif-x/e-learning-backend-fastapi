# app/models/relations.py

from sqlalchemy.orm import relationship

# Import all relevant models
from .categories import Category
from .course_prepaidable_user import CoursePrepaidableUser
from .course_subscription import CourseSubscription  # <-- Import the new model
from .courses import Course
from .lecture import Lecture
from .lecture_content import LectureContent
from .user import User


def setup_relationships():
    """
    Configure all SQLAlchemy relationships between models.
    """
    # --- Existing Relationships ---
    Category.courses = relationship(
        "Course",
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    Course.category = relationship("Category", back_populates="courses")
    Course.related_course = relationship("Course", remote_side=[Course.id])

    # --- NEW: User <-> CourseSubscription <-> Course Relationships ---

    # 1. User to CourseSubscription (One-to-Many)
    # Allows you to see all subscription details for a user: user.subscriptions
    User.subscriptions = relationship(
        "CourseSubscription", back_populates="user", cascade="all, delete-orphan"
    )

    # 2. Course to CourseSubscription (One-to-Many)
    # Allows you to see all subscription details for a course: course.subscriptions
    Course.subscriptions = relationship(
        "CourseSubscription", back_populates="course", cascade="all, delete-orphan"
    )

    # 3. CourseSubscription back to User and Course (Many-to-One)
    CourseSubscription.user = relationship("User", back_populates="subscriptions")
    CourseSubscription.course = relationship("Course", back_populates="subscriptions")

    # 4. Direct Many-to-Many links (for convenience)
    # Allows you to get a list of subscribed courses directly: user.subscribed_courses
    User.subscribed_courses = relationship(
        "Course",
        secondary="course_subscriptions",  # The name of the association table
        back_populates="subscribers",
        viewonly=True,  # Important: modifications should happen on the subscription object
    )
    # Allows you to get a list of subscribed users directly: course.subscribers
    Course.subscribers = relationship(
        "User",
        secondary="course_subscriptions",
        back_populates="subscribed_courses",
        viewonly=True,
    )

    User.prepaidable_courses = relationship(
        "Course",
        secondary="course_prepaidable_users",
        back_populates="prepaidable_users",
        viewonly=True,
    )
    # Allows you to get a list of prepaidable users directly: course.prepaidable_users
    Course.prepaidable_users = relationship(
        "User",
        secondary="course_prepaidable_users",
        back_populates="prepaidable_courses",
        viewonly=True,
    )

    Course.lectures = relationship(
        "Lecture",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Lecture.position",  # <-- Automatically order lectures
    )
    Lecture.course = relationship("Course", back_populates="lectures")

    # 2. Lecture to LectureContent (One-to-Many)
    Lecture.contents = relationship(
        "LectureContent",
        back_populates="lecture",
        cascade="all, delete-orphan",
        order_by="LectureContent.position",  # <-- Automatically order content
    )
    LectureContent.lecture = relationship("Lecture", back_populates="contents")

    # 3. Self-referential relationship for content dependencies (for future use)
    LectureContent.dependency = relationship(
        "LectureContent", remote_side=[LectureContent.id], backref="dependents"
    )
