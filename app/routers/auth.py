import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import jwt_manager  # Updated import
from app.models.user import User
from app.schemas.auth import (
    AdminAuthResponse,
    AdminLoginRequest,
    AuthFlowStatus,
    AuthResponse,
    DirectLoginRequest,
    LoginRequest,
    RefreshTokenRequest,
    TelegramVerificationRequest,
    TelegramVerificationResponse,
    UserRegistrationRequest,
    UserResponse,
)
from app.services.auth import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/telegram/verify", response_model=TelegramVerificationResponse)
async def verify_telegram(
    request: TelegramVerificationRequest, db: Session = Depends(get_db)
) -> TelegramVerificationResponse:
    """Step 1: Verify Telegram authentication data"""
    return auth_service.verify_telegram_auth(request, db)


@router.post("/register", response_model=AuthResponse)
async def register_user(
    request: UserRegistrationRequest, db: Session = Depends(get_db)
) -> AuthResponse:
    """Step 2: Complete user registration after Telegram verification"""
    return auth_service.register_user(request, db)


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    return auth_service.login(request, db)


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    request: RefreshTokenRequest, db: Session = Depends(get_db)
) -> AuthResponse:
    """Refresh access token using refresh token"""
    return auth_service.refresh_token(request.refresh_token, db)


@router.post("/logout")
async def logout(
    current_user: Annotated[User, Depends(get_current_user)],
    token: str = Depends(jwt_manager.extract_token),
) -> dict:
    """Logout current user"""
    return auth_service.logout_user(token)


@router.post("/logout-all")
async def logout_all_devices(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> dict:
    """Logout from all devices"""
    return auth_service.logout_all_devices(current_user.id, db)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Get current user information"""
    return auth_service._user_to_response(current_user)


@router.get("/status")
async def get_auth_status(
    telegram_hash: str, db: Session = Depends(get_db)
) -> AuthFlowStatus:
    """Get authentication flow status"""
    return auth_service.get_auth_status(telegram_hash, db)


@router.post("/telegram/verify/debug", include_in_schema=False)
async def verify_telegram_debug(
    request: TelegramVerificationRequest, db: Session = Depends(get_db)
) -> dict:
    """Debug endpoint for telegram verification"""
    auth_data = request.telegram_auth.dict()
    received_hash = auth_data.pop("hash", "")

    # Create data check string
    data_check_arr = []
    for key, value in sorted(auth_data.items()):
        if value is not None:
            data_check_arr.append(f"{key}={value}")

    data_check_string = "\n".join(data_check_arr)

    # Create secret key
    secret_key = hashlib.sha256(settings.telegram_bot_token.encode()).digest()

    # Calculate hash
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    return {
        "received_hash": received_hash,
        "calculated_hash": calculated_hash,
        "data_check_string": data_check_string,
        "bot_token_prefix": (
            settings.telegram_bot_token[:5] if settings.telegram_bot_token else None
        ),
        "match": calculated_hash == received_hash,
    }


# ==================== ADMIN AUTHENTICATION ====================


@router.post("/admin/login", response_model=AdminAuthResponse)
async def admin_login(
    request: AdminLoginRequest, db: Session = Depends(get_db)
) -> AdminAuthResponse:
    """
    Admin login with username or email and password.

    - **username_or_email**: Admin username or email
    - **password**: Admin password
    - **remember_me**: Keep login session longer

    Returns admin access token and admin profile.
    """
    return auth_service.admin_login(request, db)
