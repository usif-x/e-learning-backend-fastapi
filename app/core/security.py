# core/security.py
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)


def get_user_by_id(user_id: int, db: Session):
    """Fetch user info by ID using a provided DB session."""
    # This function now USES the session it's given, it doesn't create it.
    user = db.query(User).filter(User.id == user_id).first()
    return user


class JWTManager:
    """JWT token management for authentication"""

    def __init__(self):
        self.secret_key = settings.jwt_secret
        self.algorithm = settings.jwt_algorithm
        self.user_token_expire = timedelta(days=settings.jwt_user_expiration)
        self.refresh_token_expire = timedelta(days=settings.jwt_refresh_expiration)
        self.admin_token_expire = timedelta(days=settings.jwt_admin_expiration)
        self.issuer = settings.jwt_issuer

    def create_access_token(
        self,
        user: User,
        remember_me: bool = False,
        custom_expiration: Optional[timedelta] = None,
        login_time: Optional[datetime] = None,
    ) -> str:
        """
        Create JWT access token for user

        Args:
            user: User model instance
            remember_me: Extend token lifetime if True
            custom_expiration: Override default expiration

        Returns:
            JWT access token string
        """
        try:
            # Determine expiration
            if custom_expiration:
                expire = datetime.utcnow() + custom_expiration
            elif remember_me:
                expire = datetime.utcnow() + timedelta(days=30)
            elif user.status == "admin":
                expire = datetime.utcnow() + self.admin_token_expire
            else:
                expire = datetime.utcnow() + self.user_token_expire

            # Create payload
            current_time = datetime.utcnow()
            issued_at = login_time if login_time else current_time

            payload = {
                "sub": str(user.id),  # Subject (user ID)
                "telegram_id": user.telegram_id,
                "user_id": user.id,
                "role": user.status,
                "email": user.email,
                "phone": user.phone_number,
                "verified": user.is_verified,
                "exp": int(expire.timestamp()),
                "iat": int(issued_at.timestamp()),
                "iss": self.issuer,
                "type": "access",
                "user_updated": int(user.updated_at.timestamp()),  # For invalidation
            }

            # Create token
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Access token created for user: {user.telegram_id}")

            return token

        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create access token",
            )

    def create_refresh_token(
        self,
        user: User,
        remember_me: bool = False,
        custom_expiration: Optional[timedelta] = None,
    ) -> str:
        """
        Create JWT refresh token for user

        Args:
            user: User model instance
            remember_me: Extend token lifetime if True
            custom_expiration: Override default expiration

        Returns:
            JWT refresh token string
        """
        try:
            # Determine expiration
            if custom_expiration:
                expire = datetime.utcnow() + custom_expiration
            elif remember_me:
                expire = datetime.utcnow() + timedelta(days=90)
            else:
                expire = datetime.utcnow() + self.refresh_token_expire

            # Create payload (minimal for security)
            current_time = datetime.utcnow()
            payload = {
                "sub": str(user.id),
                "telegram_id": user.telegram_id,
                "user_id": user.id,
                "exp": int(expire.timestamp()),
                "iat": int(current_time.timestamp()),
                "iss": self.issuer,
                "type": "refresh",
                "user_updated": int(user.updated_at.timestamp()),
            }

            # Create token
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Refresh token created for user: {user.telegram_id}")

            return token

        except Exception as e:
            logger.error(f"Failed to create refresh token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create refresh token",
            )

    def create_token_pair(
        self, user: User, remember_me: bool = False, login_time: datetime = None
    ) -> Tuple[str, str]:
        """
        Create both access and refresh tokens

        Args:
            user: User model instance
            remember_me: Extend token lifetime if True

        Returns:
            Tuple of (access_token, refresh_token)
        """
        access_token = self.create_access_token(
            user=user, remember_me=remember_me, login_time=login_time
        )
        refresh_token = self.create_refresh_token(user, remember_me)

        return access_token, refresh_token

    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verify and decode JWT token
        """
        try:
            # Decode token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": True},
            )

            # Verify token type (check 'type' field, not 'role')
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type. Expected {token_type}",
                )

            # Verify issuer
            if payload.get("iss") != self.issuer:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token issuer",
                )

            return payload

        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token verification failed",
            )

    def extract_user_data(self, token: str) -> Dict[str, Any]:
        """
        Extract user data from access token without full verification
        (useful for getting user info from potentially expired tokens)

        Args:
            token: JWT token string

        Returns:
            User data from token payload
        """
        try:
            # Decode without verification (for expired tokens)
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False, "verify_signature": True},
            )

            return {
                "user_id": payload.get("user_id"),
                "telegram_id": payload.get("telegram_id"),
                "role": payload.get("role"),
                "email": payload.get("email"),
                "phone": payload.get("phone"),
                "verified": payload.get("verified"),
                "user_updated": payload.get("user_updated"),
            }

        except JWTError as e:
            logger.warning(f"Failed to extract user data from token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format"
            )

    def is_token_valid_for_user(self, token: str, user: User) -> bool:
        """
        Check if token is still valid for the given user
        (checks if user was updated after token creation)

        Args:
            token: JWT token string
            user: Current user from database

        Returns:
            True if token is still valid, False otherwise
        """
        try:
            user_data = self.extract_user_data(token)
            token_user_updated = user_data.get("user_updated", 0)
            current_user_updated = int(user.updated_at.timestamp())

            # Token is invalid if user was updated after token creation
            return token_user_updated >= current_user_updated

        except Exception:
            return False

    def get_token_expiration(self, token: str) -> Optional[datetime]:
        """
        Get token expiration datetime

        Args:
            token: JWT token string

        Returns:
            Token expiration datetime or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False},
            )

            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp)

            return None

        except Exception:
            return None

    def is_token_expired(self, token: str) -> bool:
        """
        Check if token is expired

        Args:
            token: JWT token string

        Returns:
            True if token is expired, False otherwise
        """
        expiration = self.get_token_expiration(token)
        if expiration:
            return datetime.utcnow() > expiration
        return True

    def create_reset_token(self, user: User, purpose: str = "password_reset") -> str:
        """
        Create special purpose token (password reset, email verification, etc.)

        Args:
            user: User model instance
            purpose: Token purpose identifier

        Returns:
            Special purpose JWT token
        """
        try:
            # Short expiration for security
            expire = datetime.utcnow() + timedelta(hours=1)

            payload = {
                "sub": str(user.id),
                "telegram_id": user.telegram_id,
                "user_id": user.id,
                "purpose": purpose,
                "exp": int(expire.timestamp()),
                "iat": int(datetime.utcnow().timestamp()),
                "iss": self.issuer,
                "type": "special",
            }

            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(
                f"Special token created for user: {user.telegram_id}, purpose: {purpose}"
            )

            return token

        except Exception as e:
            logger.error(f"Failed to create special token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create special token",
            )

    def verify_reset_token(self, token: str, expected_purpose: str) -> Dict[str, Any]:
        """
        Verify special purpose token

        Args:
            token: JWT token string
            expected_purpose: Expected token purpose

        Returns:
            Decoded token payload
        """
        try:
            payload = self.verify_token(token, "special")

            if payload.get("purpose") != expected_purpose:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token purpose",
                )

            return payload

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Special token verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid special token"
            )

    def extract_token(
        self, authorization: str = Header(..., description="Bearer token")
    ) -> str:
        """Extract token from authorization header"""
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return token
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )


class TokenBlacklist:
    """Token blacklist management using Redis"""

    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self._memory_blacklist = set()  # Fallback for when Redis is unavailable

    def add_token(self, token: str, ttl: Optional[int] = None) -> bool:
        """
        Add token to blacklist

        Args:
            token: JWT token to blacklist
            ttl: Time to live in seconds (optional)

        Returns:
            True if successfully added, False otherwise
        """
        try:
            if self.redis_client:
                # Use Redis for distributed blacklist
                ttl = ttl or int(
                    timedelta(days=settings.jwt_refresh_expiration).total_seconds()
                )
                return bool(self.redis_client.setex(f"blacklist:{token}", ttl, "1"))
            else:
                # Fallback to memory (not recommended for production)
                self._memory_blacklist.add(token)
                return True

        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
            return False

    def is_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted

        Args:
            token: JWT token to check

        Returns:
            True if token is blacklisted, False otherwise
        """
        try:
            if self.redis_client:
                return bool(self.redis_client.get(f"blacklist:{token}"))
            else:
                return token in self._memory_blacklist

        except Exception as e:
            logger.error(f"Failed to check token blacklist: {e}")
            return False

    def remove_token(self, token: str) -> bool:
        """
        Remove token from blacklist

        Args:
            token: JWT token to remove

        Returns:
            True if successfully removed, False otherwise
        """
        try:
            if self.redis_client:
                return bool(self.redis_client.delete(f"blacklist:{token}"))
            else:
                self._memory_blacklist.discard(token)
                return True

        except Exception as e:
            logger.error(f"Failed to remove token from blacklist: {e}")
            return False

    def clear_user_tokens(self, user_id: int) -> bool:
        """
        Clear all tokens for a specific user (logout from all devices)
        This is achieved by adding a user-specific blacklist entry

        Args:
            user_id: User ID to clear tokens for

        Returns:
            True if successfully cleared, False otherwise
        """
        try:
            if self.redis_client:
                # Set a flag that invalidates all tokens for this user
                ttl = int(
                    timedelta(days=settings.jwt_refresh_expiration).total_seconds()
                )
                return bool(
                    self.redis_client.setex(
                        f"user_logout:{user_id}",
                        ttl,
                        str(datetime.utcnow().timestamp()),
                    )
                )
            else:
                # For memory fallback, we can't efficiently clear all user tokens
                logger.warning("Cannot clear user tokens efficiently without Redis")
                return False

        except Exception as e:
            logger.error(f"Failed to clear user tokens: {e}")
            return False

    def is_user_logged_out(self, user_id: int, token_issued_at: datetime) -> bool:
        """
        Check if user was logged out from all devices after token was issued

        Args:
            user_id: User ID to check
            token_issued_at: When the token was issued

        Returns:
            True if user was logged out after token was issued
        """
        try:
            if self.redis_client:
                logout_timestamp = self.redis_client.get(f"user_logout:{user_id}")
                if logout_timestamp:
                    logout_time = datetime.fromtimestamp(float(logout_timestamp))
                    return logout_time > token_issued_at
            return False

        except Exception as e:
            logger.error(f"Failed to check user logout status: {e}")
            return False


# Global instances
jwt_manager = JWTManager()

# Initialize token blacklist (will be set up with Redis in main app)
token_blacklist = TokenBlacklist()
