# services/auth_service.py
import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import redis
from fastapi import HTTPException, status
from jose import jwt
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.hasher import PasswordHelper
from app.core.security import jwt_manager, token_blacklist
from app.models.admin import Admin
from app.models.user import User
from app.schemas.auth import (
    AdminAuthResponse,
    AdminLoginRequest,
    AdminResponse,
    AuthFlowStatus,
    AuthResponse,
    DirectLoginRequest,
    LoginRequest,
    TelegramVerificationRequest,
    TelegramVerificationResponse,
    UserRegistrationRequest,
    UserResponse,
)

# Setup logging
logger = logging.getLogger(__name__)

# Setup Redis for temporary data storage
try:
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    logger.info("Redis connection established for auth service")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
    redis_client = None

# In-memory fallback for temporary telegram data
_telegram_hashes = {}  # telegram_hash -> telegram_data


class TelegramHelper:
    """Helper class for Telegram authentication operations"""

    @staticmethod
    def verify_telegram_hash(auth_data: Dict[str, Any]) -> bool:
        """Verify telegram authentication hash"""
        try:
            if not settings.telegram_bot_token:
                logger.error("Telegram bot token not configured")
                return False

            data_check_arr = []
            auth_hash = auth_data.pop("hash", "")

            logger.debug(f"Verifying telegram data: {auth_data}")
            logger.debug(f"Auth hash from telegram: {auth_hash}")

            for key, value in sorted(auth_data.items()):
                if value:
                    data_check_arr.append(f"{key}={value}")

            data_check_string = "\n".join(data_check_arr)
            logger.debug(f"Data check string: {data_check_string}")

            secret_key = hashlib.sha256(settings.telegram_bot_token.encode()).digest()
            logger.debug(f"Bot token used: {settings.telegram_bot_token[:5]}...")

            calculated_hash = hmac.new(
                secret_key,
                data_check_string.encode(),
                hashlib.sha256,
            ).hexdigest()

            logger.debug(f"Calculated hash: {calculated_hash}")
            logger.debug(f"Hashes match: {calculated_hash == auth_hash}")

            return calculated_hash == auth_hash

        except Exception as e:
            logger.error(f"Error verifying telegram hash: {e}")
            return False

    @staticmethod
    def generate_telegram_hash(telegram_data: Dict[str, Any]) -> str:
        """Generate temporary hash for telegram session"""
        data_string = f"{telegram_data['id']}_{telegram_data['auth_date']}_{secrets.token_hex(16)}"
        return hashlib.sha256(data_string.encode()).hexdigest()

    @staticmethod
    def store_telegram_data(temp_hash: str, telegram_data: Dict[str, Any]) -> bool:
        """Store telegram data temporarily (30 minutes)"""
        try:
            if redis_client:
                redis_client.setex(
                    f"telegram_hash:{temp_hash}",
                    int(timedelta(minutes=30).total_seconds()),
                    json.dumps(telegram_data),
                )
            else:
                _telegram_hashes[temp_hash] = {
                    "data": telegram_data,
                    "expires": datetime.utcnow() + timedelta(minutes=30),
                }
            return True
        except Exception as e:
            logger.error(f"Failed to store telegram data: {e}")
            return False

    @staticmethod
    def get_telegram_data(temp_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored telegram data"""
        try:
            if redis_client:
                data = redis_client.get(f"telegram_hash:{temp_hash}")
                return json.loads(data) if data else None
            else:
                if temp_hash in _telegram_hashes:
                    stored = _telegram_hashes[temp_hash]
                    if datetime.utcnow() < stored["expires"]:
                        return stored["data"]
                    else:
                        del _telegram_hashes[temp_hash]
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve telegram data: {e}")
            return None

    @staticmethod
    def cleanup_telegram_data(temp_hash: str):
        """Clean up temporary telegram data"""
        try:
            if redis_client:
                redis_client.delete(f"telegram_hash:{temp_hash}")
            else:
                _telegram_hashes.pop(temp_hash, None)
        except Exception as e:
            logger.error(f"Failed to cleanup telegram data: {e}")

    @staticmethod
    def get_display_name(telegram_data: Dict[str, Any]) -> str:
        """Get display name from telegram data"""
        first_name = telegram_data.get("first_name", "")
        last_name = telegram_data.get("last_name", "")
        return f"{first_name} {last_name}".strip() if last_name else first_name


class AuthService:
    def __init__(self):
        self.password_helper = PasswordHelper()
        self.telegram_helper = TelegramHelper()

    def verify_telegram_auth(
        self, request: TelegramVerificationRequest, db: Session
    ) -> TelegramVerificationResponse:
        """
        Step 1: Verify telegram authentication data
        """
        try:
            # The 'db' parameter is already the SQLAlchemy Session object provided by
            # FastAPI's dependency injection. There is no need to call next(db).
            # The incorrect block that caused the TypeError has been removed.

            # Get the nested telegram data from the request
            telegram_data = request.telegram_auth

            # Create a copy for hash verification, as the function modifies the dict
            auth_data_copy = telegram_data.dict().copy()
            if not self.telegram_helper.verify_telegram_hash(auth_data_copy):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid telegram authentication data",
                )

            # Check if a user with this Telegram ID already exists
            existing_user = (
                db.query(User).filter(User.telegram_id == str(telegram_data.id)).first()
            )

            # Generate and store a temporary hash for the next step (login/register)
            temp_hash = self.telegram_helper.generate_telegram_hash(
                telegram_data.dict()
            )
            if not self.telegram_helper.store_telegram_data(
                temp_hash, telegram_data.dict()
            ):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to store telegram session data",
                )

            if existing_user:
                # User exists - immediately log them in and create tokens
                existing_user.telegram_verified = True
                existing_user.telegram_verified_at = datetime.utcnow()

                if existing_user.telegram_username != telegram_data.username:
                    existing_user.telegram_username = telegram_data.username
                if (
                    telegram_data.photo_url
                    and existing_user.profile_picture != telegram_data.photo_url
                ):
                    existing_user.profile_picture = telegram_data.photo_url

                # Update last login
                login_time = datetime.utcnow()
                existing_user.last_login = login_time
                db.commit()
                db.refresh(existing_user)

                # Generate tokens immediately
                access_token, refresh_token = jwt_manager.create_token_pair(
                    user=existing_user, login_time=login_time
                )

                # Clean up telegram hash since we're not using it for login
                self.telegram_helper.cleanup_telegram_data(temp_hash)

                logger.info(f"User auto-login successful: {existing_user.telegram_id}")

                return TelegramVerificationResponse(
                    telegram_verified=True,
                    user_exists=True,
                    success=True,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_type="bearer",
                    expires_in=int(
                        timedelta(minutes=settings.jwt_user_expiration).total_seconds()
                    ),
                    user=self._user_to_response(existing_user),
                    user_data={
                        "id": existing_user.id,
                        "display_name": existing_user.display_name,
                        "login_methods": self._get_user_login_methods(existing_user),
                    },
                    message="Telegram verified and user logged in successfully.",
                    next_step="authenticated",
                )
            else:
                # New user, proceed to registration step
                return TelegramVerificationResponse(
                    telegram_verified=True,
                    user_exists=False,
                    telegram_hash=temp_hash,
                    message="Telegram verified. New user. Proceed to registration.",
                    next_step="register",
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Telegram verification error: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Telegram verification failed",
            )

    def register_user(
        self, request: UserRegistrationRequest, db: Session
    ) -> AuthResponse:
        """
        Step 2: Register new user after telegram verification
        """
        try:
            telegram_data = self.telegram_helper.get_telegram_data(
                request.telegram_hash
            )
            if not telegram_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired telegram hash. Please verify again.",
                )

            existing_user = (
                db.query(User)
                .filter(
                    or_(
                        User.telegram_id == str(telegram_data["id"]),
                        User.email == request.email if request.email else False,
                        (
                            User.phone_number == request.phone_number
                            if request.phone_number
                            else False
                        ),
                    )
                )
                .first()
            )

            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User already exists with this telegram, email, or phone number",
                )

            hashed_password = None
            if request.password:
                hashed_password = self.password_helper.hash_password(request.password)

            full_name = request.full_name or self.telegram_helper.get_display_name(
                telegram_data
            )

            new_user = User(
                email=request.email,
                hashed_password=hashed_password,
                full_name=full_name,
                phone_number=request.phone_number,
                parent_phone_number=request.parent_phone_number,
                profile_picture=telegram_data.get("photo_url"),
                is_active=True,
                is_verified=settings.verify_user_model,
                status=request.role or settings.authorization_default_role,
                telegram_id=str(telegram_data["id"]),
                telegram_username=telegram_data.get("username"),
                telegram_first_name=telegram_data.get("first_name"),
                telegram_last_name=telegram_data.get("last_name"),
                telegram_verified=True,
                telegram_verified_at=datetime.utcnow(),
            )

            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            access_token, refresh_token = jwt_manager.create_token_pair(new_user)
            new_user.last_login = datetime.utcnow()
            db.commit()

            self.telegram_helper.cleanup_telegram_data(request.telegram_hash)
            logger.info(f"User registered successfully: {new_user.telegram_id}")

            return AuthResponse(
                success=True,
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=int(
                    timedelta(minutes=settings.jwt_user_expiration).total_seconds()
                ),
                user=self._user_to_response(new_user),
                message="User registered and logged in successfully.",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Registration error: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed",
            )

    # ... (rest of the file is correct and unchanged) ...
    def login(self, request: LoginRequest, db: Session) -> AuthResponse:
        """
        Step 3: Login existing user after telegram verification
        """
        try:
            # Verify telegram hash and get telegram data
            telegram_data = self.telegram_helper.get_telegram_data(
                request.telegram_hash
            )
            if not telegram_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired telegram hash. Please verify again.",
                )

            user = (
                db.query(User)
                .filter(User.telegram_id == str(telegram_data["id"]))
                .first()
            )

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found for this Telegram account.",
                )

            # If login method is email, verify password
            if request.login_method == "email":
                if not user.hashed_password or not self.password_helper.check_password(
                    request.password, user.hashed_password
                ):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid email or password",
                    )
            elif request.login_method == "phone":
                # For phone login, just verify the phone number matches
                if user.phone_number != request.phone_number:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid phone number",
                    )

            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account not found or deactivated",
                )
            login_time = datetime.utcnow()
            # Generate tokens
            access_token, refresh_token = jwt_manager.create_token_pair(
                user=user, login_time=login_time
            )

            # Update last login
            user.last_login = login_time
            db.commit()

            # Clean up telegram hash
            self.telegram_helper.cleanup_telegram_data(request.telegram_hash)

            logger.info(
                f"User login successful: {user.telegram_id} via {request.login_method}"
            )

            return AuthResponse(
                success=True,
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=int(
                    timedelta(minutes=settings.jwt_user_expiration).total_seconds()
                ),
                user=self._user_to_response(user),
                message=f"Login successful via {request.login_method}",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed"
            )

    def direct_login(self, request: DirectLoginRequest, db: Session) -> AuthResponse:
        """
        Direct login for returning users (without telegram verification)
        """
        try:
            user = None

            if request.login_method == "email":
                user = db.query(User).filter(User.email == request.email).first()
                if (
                    not user
                    or not user.hashed_password
                    or not self.password_helper.check_password(
                        request.password, user.hashed_password
                    )
                ):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid email or password",
                    )

            elif request.login_method == "phone":
                user = (
                    db.query(User)
                    .filter(User.phone_number == request.phone_number)
                    .first()
                )
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Phone number not found",
                    )
                # If password is provided, verify it
                if request.password and user.hashed_password:
                    if not self.password_helper.check_password(
                        request.password, user.hashed_password
                    ):
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid phone number or password",
                        )

            elif request.login_method == "telegram":
                user = (
                    db.query(User)
                    .filter(User.telegram_id == request.telegram_id)
                    .first()
                )
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Telegram user not found",
                    )

            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account not found or deactivated",
                )

            # Generate tokens
            access_token, refresh_token = jwt_manager.create_token_pair(
                user, remember_me=request.remember_me
            )

            # Update last login
            user.last_login = datetime.utcnow()
            db.commit()

            logger.info(
                f"Direct login successful: {user.telegram_id} via {request.login_method}"
            )

            return AuthResponse(
                success=True,
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=int(
                    timedelta(minutes=settings.jwt_user_expiration).total_seconds()
                ),
                user=self._user_to_response(user),
                message=f"Direct login successful via {request.login_method}",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Direct login error: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Direct login failed",
            )

    # ==================== LOGOUT ====================

    def logout_user(self, token: str) -> Dict[str, Any]:
        """
        Logout user by blacklisting the token
        """
        try:
            # Verify token first to get expiration
            payload = jwt_manager.verify_token(token, "access")

            # Calculate TTL until token expiration
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                exp_datetime = datetime.fromtimestamp(exp_timestamp)
                ttl = int((exp_datetime - datetime.utcnow()).total_seconds())

                if ttl > 0:
                    # Add token to blacklist
                    if not token_blacklist.add_token(token, ttl):
                        logger.warning(
                            "Failed to blacklist token, but continuing with logout"
                        )

            logger.info(f"User logged out successfully: {payload.get('telegram_id')}")

            return {"success": True, "message": "Logout successful"}

        except HTTPException as e:
            # Token might be invalid, but that's ok for logout
            logger.info(f"Logout attempted with invalid token: {e.detail}")
            return {"success": True, "message": "Logout successful"}
        except Exception as e:
            logger.error(f"Logout error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout failed",
            )

    def logout_all_devices(self, user_id: int, db: Session) -> Dict[str, Any]:
        """
        Logout user from all devices by invalidating all tokens
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )

            # Method 1: Clear all tokens using token blacklist
            if not token_blacklist.clear_user_tokens(user_id):
                # Method 2: Fallback - update user timestamp to invalidate tokens
                user.updated_at = datetime.utcnow()
                db.commit()

            logger.info(f"User logged out from all devices: {user.telegram_id}")

            return {"success": True, "message": "Logged out from all devices"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Logout all devices error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout from all devices failed",
            )

    # ==================== TOKEN MANAGEMENT ====================

    def refresh_token(self, refresh_token: str, db: Session) -> AuthResponse:
        """
        Refresh access token using refresh token
        """
        try:
            # Check if token is blacklisted
            if token_blacklist.is_blacklisted(refresh_token):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                )

            # Verify refresh token
            payload = jwt_manager.verify_token(refresh_token, "refresh")

            telegram_id = payload.get("telegram_id")
            user_id = payload.get("user_id")

            if not telegram_id or not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                )

            # Get user from database
            user = (
                db.query(User)
                .filter(User.id == user_id, User.telegram_id == telegram_id)
                .first()
            )
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive",
                )

            # Check if token is still valid for this user (check if user was updated after token creation)
            if not jwt_manager.is_token_valid_for_user(refresh_token, user):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token is no longer valid for this user",
                )

            # Generate new token pair
            new_access_token, new_refresh_token = jwt_manager.create_token_pair(user)

            # Blacklist old refresh token
            token_blacklist.add_token(refresh_token)

            logger.info(f"Token refreshed for user: {user.telegram_id}")

            return AuthResponse(
                success=True,
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
                expires_in=int(
                    timedelta(minutes=settings.jwt_user_expiration).total_seconds()
                ),
                user=self._user_to_response(user),
                message="Token refreshed successfully",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token refresh failed",
            )

    def get_current_user(self, token: str, db: Session) -> User:
        """
        Get current user from JWT token
        """
        try:
            # Check if token is blacklisted
            if token_blacklist.is_blacklisted(token):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Verify access token
            payload = jwt_manager.verify_token(token, "access")

            telegram_id = payload.get("telegram_id")
            user_id = payload.get("user_id")

            if not telegram_id or not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Get user from database
            user = (
                db.query(User)
                .filter(User.id == user_id, User.telegram_id == telegram_id)
                .first()
            )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is deactivated",
                )

            # Check if token is still valid for this user
            if not jwt_manager.is_token_valid_for_user(token, user):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token is no longer valid for this user",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Check if user was logged out from all devices
            token_issued_at = datetime.fromtimestamp(payload.get("iat", 0))
            if token_blacklist.is_user_logged_out(user.id, token_issued_at):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User was logged out from all devices",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get current user error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # ==================== UTILITY METHODS ====================

    def get_auth_status(self, telegram_hash: str, db: Session) -> AuthFlowStatus:
        """
        Get authentication flow status
        """
        telegram_data = self.telegram_helper.get_telegram_data(telegram_hash)
        if not telegram_data:
            return AuthFlowStatus(
                telegram_verified=False,
                user_registered=False,
                login_methods=[],
                requires_password=False,
                message="Telegram verification required",
            )

        user = db.query(User).filter(User.telegram_id == telegram_data["id"]).first()

        if not user:
            return AuthFlowStatus(
                telegram_verified=True,
                user_registered=False,
                login_methods=[],
                requires_password=False,
                message="Registration required",
            )

        login_methods = self._get_user_login_methods(user)
        requires_password = "email" in login_methods and bool(user.email)

        return AuthFlowStatus(
            telegram_verified=True,
            user_registered=True,
            login_methods=login_methods,
            requires_password=requires_password,
            user_role=user.status,
            message="Ready for login",
        )

    def validate_user_permissions(self, user: User, required_role: str) -> bool:
        """
        Validate if user has required role/permission
        """
        role_hierarchy = {"student": 1, "teacher": 2, "admin": 3}

        user_level = role_hierarchy.get(user.status, 0)
        required_level = role_hierarchy.get(required_role, 0)

        return user_level >= required_level

    def _get_user_login_methods(self, user: User) -> list[str]:
        """Get available login methods for user"""
        methods = []
        if user.email and user.hashed_password:
            methods.append("email")
        if user.phone_number:
            methods.append("phone")
        if user.telegram_id:
            methods.append("telegram")
        return methods

    def _user_to_response(self, user: User) -> UserResponse:
        """Convert User model to UserResponse"""
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            display_name=user.display_name,
            phone_number=user.phone_number,
            parent_phone_number=user.parent_phone_number,
            profile_picture=user.profile_picture,
            is_active=user.is_active,
            is_verified=user.is_verified,
            status=user.status,
            wallet_balance=user.wallet_balance,
            telegram_id=user.telegram_id,
            telegram_username=user.telegram_username,
            telegram_first_name=user.telegram_first_name,
            telegram_last_name=user.telegram_last_name,
            telegram_verified=user.telegram_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
            identifier=user.identifier,
            login_methods=self._get_user_login_methods(user),
        )

    def admin_login(self, request: AdminLoginRequest, db: Session) -> AdminAuthResponse:
        """
        Admin login with username or email and password
        """
        try:
            # Find admin by username or email
            admin = (
                db.query(Admin)
                .filter(
                    or_(
                        Admin.username == request.username_or_email,
                        Admin.email == request.username_or_email,
                    )
                )
                .first()
            )

            if not admin:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials",
                )

            # Verify password
            if not self.password_helper.check_password(
                request.password, admin.password
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials",
                )

            # Check if admin is verified
            if not admin.is_verified:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin account is not verified",
                )

            # Generate tokens with admin expiration (manually since Admin model is different from User)
            login_time = datetime.utcnow()

            # Create access token
            access_expire = login_time + timedelta(days=settings.jwt_admin_expiration)
            access_payload = {
                "sub": str(admin.id),
                "admin_id": admin.id,
                "username": admin.username,
                "email": admin.email,
                "role": "admin",
                "level": admin.level,
                "type": "access",  # Add type field for token verification
                "iat": int(login_time.timestamp()),
                "exp": int(access_expire.timestamp()),
                "iss": settings.jwt_issuer,
            }
            access_token = jwt.encode(
                access_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
            )

            # Create refresh token
            refresh_expire = login_time + timedelta(
                days=settings.jwt_admin_expiration * 3
            )
            refresh_payload = {
                "sub": str(admin.id),
                "admin_id": admin.id,
                "username": admin.username,
                "role": "admin",
                "type": "refresh",  # Add type field for refresh token
                "iat": int(login_time.timestamp()),
                "exp": int(refresh_expire.timestamp()),
                "iss": settings.jwt_issuer,
            }
            refresh_token = jwt.encode(
                refresh_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
            )

            logger.info(
                f"Admin login successful: {admin.username} (Level: {admin.level})"
            )

            return AdminAuthResponse(
                success=True,
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=int(
                    timedelta(days=settings.jwt_admin_expiration).total_seconds()
                ),
                admin=AdminResponse(
                    id=admin.id,
                    name=admin.name,
                    username=admin.username,
                    email=admin.email,
                    is_verified=admin.is_verified,
                    level=admin.level,
                    created_at=admin.created_at,
                    updated_at=admin.updated_at,
                ),
                message="Admin login successful",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Admin login error: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Admin login failed",
            )


auth_service = AuthService()
