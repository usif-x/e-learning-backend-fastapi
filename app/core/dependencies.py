from datetime import datetime
from typing import Annotated, Optional, Union

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import jwt_manager
from app.models.course_prepaidable_user import CoursePrepaidableUser
from app.models.course_subscription import CourseSubscription
from app.models.courses import Course
from app.models.user import User
from app.schemas.auth import TokenData

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency that requires a valid Bearer token and returns the active user.
    Raises 401 Unauthorized if the token is missing, invalid, or the user is not found.
    """
    # --- THIS IS THE FIX ---
    # 1. Check if the Authorization header was provided at all.
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. If the header exists, safely get the token and verify it.
    token = credentials.credentials
    payload = jwt_manager.verify_token(token, token_type="access")

    user_id: Optional[int] = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user_id",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Find the user in the database.
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # 4. (Optional but good practice) Check if token was issued before the last logout/password change
    # Note: This requires last_login to be updated on password change/logout as well.
    if user.last_login and payload.get("iat") < int(user.last_login.timestamp()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: Session = Depends(get_db),
) -> Union[User, bool]:
    """
    Dependency اختياري:
    - لو فيه Bearer token → يرجّع user
    - لو مفيش → يرجّع True (يكمل عادي)
    """
    if credentials is None:  # مفيش Authorization header
        return True

    token = credentials.credentials
    payload = jwt_manager.verify_token(token, token_type="access")

    user_id: Optional[int] = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user_id",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # تحقق من last_login مقابل iat
    if payload.get("iat") < int(user.last_login.timestamp()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token revoked",
        )

    return user


async def get_current_active_verified_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency to get current active and verified user
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User not verified"
        )
    return current_user


async def get_enrolled_course_for_current_user(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # <-- Requires a logged-in user
) -> Course:
    """
    Dependency to check if the current user is enrolled in a course.

    - Fetches the course by its ID.
    - Checks for an active subscription OR a prepaidable entry.
    - Raises 404 if the course doesn't exist.
    - Raises 403 if the user is not enrolled.
    - Returns the Course object on success.
    """
    # 1. First, find the course. If it doesn't exist, it's a 404.
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    # 2. Check for an active subscription. We use .exists() for performance.
    is_subscribed = db.query(
        db.query(CourseSubscription)
        .filter(
            CourseSubscription.user_id == current_user.id,
            CourseSubscription.course_id == course_id,
            CourseSubscription.is_active
            == True,  # Important: only check for active subs
        )
        .exists()
    ).scalar()

    if is_subscribed:
        return course  # User is enrolled, return the course object.

    # 3. If not subscribed, check for prepaidable access.
    is_prepaidable = db.query(
        db.query(CoursePrepaidableUser)
        .filter(
            CoursePrepaidableUser.user_id == current_user.id,
            CoursePrepaidableUser.course_id == course_id,
        )
        .exists()
    ).scalar()

    if is_prepaidable:
        return course  # User is enrolled, return the course object.

    # 4. If neither check passed, the user is not enrolled.
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You are not enrolled in this course.",
    )


def get_user_by_tg_id(chat_id: int, db: Session):
    """Fetch user info by Telegram chat_id using a provided DB session."""
    # This function now USES the session it's given, it doesn't create it.
    user = db.query(User).filter(User.telegram_id == chat_id).first()
    return user
