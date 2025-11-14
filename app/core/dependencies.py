from datetime import datetime
from typing import Annotated, Optional, Union

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import jwt_manager
from app.models.admin import Admin
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


def get_user_by_tg_id(chat_id: int, db: Session):
    """Fetch user info by Telegram chat_id using a provided DB session."""
    # This function now USES the session it's given, it doesn't create it.
    user = db.query(User).filter(User.telegram_id == chat_id).first()
    return user


async def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: Session = Depends(get_db),
) -> Admin:
    """
    Dependency that requires a valid Bearer token and returns the authenticated admin.
    Raises 401 Unauthorized if the token is missing, invalid, or the admin is not found.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        # Decode the token
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )

        # Verify token type is admin
        token_type = payload.get("type")
        if token_type != "admin":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get admin_id from payload
        admin_id: Optional[int] = payload.get("admin_id")
        if admin_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing admin_id",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Find the admin in the database
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not admin.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is not verified",
        )

    return admin


async def get_optional_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: Session = Depends(get_db),
) -> Union[Admin, bool]:
    """
    Optional admin dependency:
    - If Bearer token exists and valid → returns Admin
    - If no token → returns True (continues without auth)
    """
    if credentials is None:
        return True

    token = credentials.credentials

    try:
        # Decode the token
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )

        # Verify token type is admin
        token_type = payload.get("type")
        if token_type != "admin":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        admin_id: Optional[int] = payload.get("admin_id")
        if admin_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing admin_id",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not admin.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is not verified",
        )

    return admin


def require_admin_level(min_level: int):
    """
    Dependency factory to require minimum admin level.
    Usage: Depends(require_admin_level(999))

    Example:
        @router.post("/admin/create")
        async def create_admin(
            admin: Admin = Depends(require_admin_level(999))
        ):
            # Only admins with level 999+ can access
            ...
    """

    async def level_checker(
        admin: Admin = Depends(get_current_admin),
    ) -> Admin:
        if admin.level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Admin level {min_level} or higher required",
            )
        return admin

    return level_checker
