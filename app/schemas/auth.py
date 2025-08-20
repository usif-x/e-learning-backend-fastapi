import hashlib
import hmac
import re
from datetime import datetime
from typing import Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.core.config import settings


# Telegram verification schemas
class TelegramAuthData(BaseModel):
    """Telegram authentication data from Telegram Login Widget"""

    id: str = Field(..., description="Telegram user ID")
    first_name: str = Field(..., description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")
    username: Optional[str] = Field(None, description="Telegram username")
    photo_url: Optional[str] = Field(None, description="Profile photo URL")
    auth_date: int = Field(..., description="Unix timestamp of authentication")
    hash: str = Field(..., description="Authentication hash from Telegram")

    @field_validator("id", mode="before")
    @classmethod
    def convert_id_to_str(cls, value):
        return str(value)


class TelegramVerificationRequest(BaseModel):
    """Step 1: Verify user through Telegram"""

    telegram_auth: TelegramAuthData

    def verify_telegram_auth(self) -> bool:
        """Verify the Telegram authentication data using bot token from settings"""
        if not settings.telegram_bot_token:
            raise ValueError("Telegram bot token not configured")

        # Create data check string
        auth_data = self.telegram_auth.dict(exclude={"hash"})
        data_check_arr = []

        for key, value in sorted(auth_data.items()):
            if value is not None:
                data_check_arr.append(f"{key}={value}")

        data_check_string = "\n".join(data_check_arr)

        # Create secret key using bot token from settings
        secret_key = hashlib.sha256(settings.telegram_bot_token.encode()).digest()

        # Calculate hash
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        return calculated_hash == self.telegram_auth.hash


class TelegramVerificationResponse(BaseModel):
    """Response after telegram verification"""

    telegram_verified: bool
    user_exists: bool
    telegram_hash: str
    user_data: Optional[dict] = None  # Existing user data if found
    message: str
    next_step: str  # "register" or "login"


# Registration schemas (after telegram verification)
class UserRegistrationRequest(BaseModel):
    """Step 2: Complete registration after telegram verification"""

    model_config = ConfigDict(from_attributes=True)

    telegram_hash: str = Field(..., description="Hash from telegram verification")
    full_name: Optional[str] = Field(None, description="Override telegram display name")
    email: Optional[EmailStr] = Field(None, description="Email address")
    phone_number: Optional[str] = Field(None, description="Phone number")
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    confirm_password: Optional[str] = Field(None, description="Password confirmation")
    parent_phone_number: Optional[str] = Field(None, max_length=20)
    role: Optional[str] = Field(
        default=settings.authorization_default_role,
        description="User role",
        pattern=f"^({'|'.join(settings.authorization_roles)})$",
    )

    @classmethod
    @model_validator(mode="before")
    def validate_registration_data(cls, values):
        if isinstance(values, dict):
            email = values.get("email")
            phone_number = values.get("phone_number")
            password = values.get("password")
            confirm_password = values.get("confirm_password")

            # At least one contact method required
            if not email and not phone_number:
                raise ValueError("Either email or phone number is required")

            # Password required for email registration
            if email and not password:
                raise ValueError("Password is required when registering with email")

            # Password not required for phone-only registration
            if not email and password:
                raise ValueError(
                    "Password should not be provided for phone-only registration"
                )

            # Password confirmation
            if password and password != confirm_password:
                raise ValueError("Passwords do not match")

            # Password strength validation (using settings)
            if password and len(password) < 8:
                raise ValueError(f"Password must be at least 8 characters long")

            if password:
                if not re.search(r"[A-Z]", password):
                    raise ValueError(
                        "Password must contain at least one uppercase letter"
                    )
                if not re.search(r"[a-z]", password):
                    raise ValueError(
                        "Password must contain at least one lowercase letter"
                    )
                if not re.search(r"\d", password):
                    raise ValueError("Password must contain at least one digit")
                if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                    raise ValueError(
                        "Password must contain at least one special character"
                    )

        return values

    @field_validator("phone_number", "parent_phone_number")
    @classmethod
    def validate_phone(cls, v):
        if v and not re.match(r"^\+?[\d\s\-\(\)]+$", v):
            raise ValueError("Invalid phone number format")
        return v


# Login schemas
class LoginRequest(BaseModel):
    """Step 3: Login after telegram verification"""

    telegram_hash: str = Field(..., description="Hash from telegram verification")
    login_method: str = Field(
        ..., pattern="^(email|phone)$", description="Login method: email or phone"
    )
    email: Optional[EmailStr] = Field(
        None, description="Email (required for email login)"
    )
    phone_number: Optional[str] = Field(
        None, description="Phone number (required for phone login)"
    )
    password: Optional[str] = Field(
        None, description="Password (required for email login)"
    )
    remember_me: bool = Field(default=False, description="Remember login")

    @classmethod
    @model_validator(mode="before")
    def validate_login_data(cls, values):
        if isinstance(values, dict):
            login_method = values.get("login_method")
            email = values.get("email")
            phone_number = values.get("phone_number")
            password = values.get("password")

            if login_method == "email":
                if not email:
                    raise ValueError("Email is required for email login")
                if not password:
                    raise ValueError("Password is required for email login")

            elif login_method == "phone":
                if not phone_number:
                    raise ValueError("Phone number is required for phone login")
                if password:
                    raise ValueError("Password should not be provided for phone login")

        return values


# Alternative direct login (without telegram hash - for returning users)
class DirectLoginRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    """Direct login for users who have already verified telegram"""

    login_method: str = Field(..., pattern="^(email|phone|telegram)$")
    email: Optional[EmailStr] = Field(None)
    phone_number: Optional[str] = Field(None)
    telegram_id: Optional[str] = Field(None)
    password: Optional[str] = Field(None)
    remember_me: bool = Field(default=False)

    @model_validator(mode="before")
    @classmethod
    def validate_direct_login(cls, values):
        login_method = values.get("login_method")
        email = values.get("email")
        phone_number = values.get("phone_number")
        telegram_id = values.get("telegram_id")
        password = values.get("password")

        if login_method == "email":
            if not email or not password:
                raise ValueError("Email and password are required for email login")
        elif login_method == "phone":
            if not phone_number:
                raise ValueError("Phone number is required for phone login")
        elif login_method == "telegram":
            if not telegram_id:
                raise ValueError("Telegram ID is required for telegram login")

        return values


# Response schemas
class AuthResponse(BaseModel):
    """Standard authentication response"""

    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None  # Will use settings.jwt_user_expiration
    user: Optional["UserResponse"] = None
    message: str


class UserResponse(BaseModel):
    """User response data"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: Optional[str]
    full_name: str
    display_name: str  # Computed from telegram names
    phone_number: Optional[str]
    parent_phone_number: Optional[str]
    profile_picture: Optional[str]
    is_active: bool
    is_verified: bool
    status: str  # Role from settings

    # Telegram data
    telegram_id: str
    telegram_username: Optional[str]
    telegram_first_name: str
    telegram_last_name: Optional[str]
    telegram_verified: bool

    wallet_balance: Optional[float]

    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]

    # Computed properties
    identifier: str  # telegram_username or user_id
    login_methods: list[str] = []  # Available login methods


# Token schemas (using settings)
class TokenData(BaseModel):
    telegram_id: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None
    exp: Optional[int] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Update schemas
class UserUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = Field(None, description="Add email if not present")
    phone_number: Optional[str] = Field(None, max_length=20)
    parent_phone_number: Optional[str] = Field(None, max_length=20)
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")

    @field_validator("phone_number", "parent_phone_number")
    @classmethod
    def validate_phone(cls, v):
        if v and not re.match(r"^\+?[\d\s\-\(\)]+$", v):
            raise ValueError("Invalid phone number format")
        return v


class SetPasswordRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    """Set password for phone-only users who want to add email login"""

    current_telegram_hash: str = Field(..., description="Current telegram verification")
    email: EmailStr = Field(..., description="Email to associate with password")
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., description="Password confirmation")

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, values):
        if "new_password" in values.data and v != values.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class PasswordUpdateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    """Update password for users who already have one"""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., description="Password confirmation")

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, values):
        if "new_password" in values.data and v != values.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


# Phone verification schemas
class PhoneVerificationRequest(BaseModel):
    phone_number: str = Field(..., description="New phone number to verify")
    telegram_hash: str = Field(..., description="Telegram verification hash")


class PhoneVerificationConfirm(BaseModel):
    phone_number: str = Field(..., description="Phone number being verified")
    verification_code: str = Field(..., description="SMS verification code")


# Role management (admin only)
class UserRoleUpdate(BaseModel):
    user_id: int = Field(..., description="User ID to update")
    new_role: str = Field(
        ...,
        description="New user role",
        pattern=f"^({'|'.join(settings.authorization_roles)})$",
    )


# Error response
class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[dict] = None


# Authentication flow status
class AuthFlowStatus(BaseModel):
    """Check current authentication flow status"""

    telegram_verified: bool
    user_registered: bool
    login_methods: list[str]  # Available login methods
    requires_password: bool
    user_role: Optional[str] = None
    message: str


# Admin schemas for user management
class UserListRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(
        default=settings.default_page_size, ge=1, le=settings.max_page_size
    )
    role: Optional[str] = Field(
        None, pattern=f"^({'|'.join(settings.authorization_roles)})$"
    )
    search: Optional[str] = Field(
        None, description="Search by name, email, or telegram username"
    )
    is_active: Optional[bool] = None


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
    page: int
    size: int
    total_pages: int


# Settings-based configuration
class AuthConfig(BaseModel):
    """Authentication configuration from settings"""

    telegram_enabled: bool = Field(default=True)
    telegram_bot_username: str = Field(default=settings.telegram_bot_username)
    authorization_methods: list[str] = Field(default=settings.authorization_methods)
    available_roles: list[str] = Field(default=settings.authorization_roles)
    default_role: str = Field(default=settings.authorization_default_role)
    jwt_expiration: int = Field(default=settings.jwt_user_expiration)
    verify_users: bool = Field(default=settings.verify_user_model)


# Rebuild models with forward references
AuthResponse.model_rebuild()
