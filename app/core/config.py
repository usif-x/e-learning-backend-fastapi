import os
from typing import List, Union

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application Information
    app_name: str = Field(default="E-Learning Platform")
    app_description: str = Field(default="Online Learning Management System")
    app_version: str = Field(default="1.0.0")
    app_url: str = Field(default="http://localhost:8000")
    debug: bool = Field(default=True)
    production: bool = Field(default=False)
    timezone: str = Field(default="UTC")
    language: str = Field(default="en")

    # Database Configuration
    db_connection: str = Field(default="postgres")  # Options: mysql, postgresql, sqlite
    db_host: str = Field(default="127.0.0.1")
    db_port: int = Field(default=5432)
    db_database: str = Field(default="e-learning")
    db_username: str = Field(default="home")
    db_password: str = Field(default="123")

    # Cache & Session Configuration
    cache_driver: str = Field(default="file")
    session_driver: str = Field(default="file")
    queue_connection: str = Field(default="sync")

    # Security Settings
    cors_allowed_origins: List[str] = Field(
        default=["http://localhost:3000"], env="CORS_ALLOWED_ORIGINS"
    )
    rate_limit_requests: int = Field(default=100)
    rate_limit_window: int = Field(default=60)
    password_hash_rounds: int = Field(default=12)

    # JWT Configuration
    jwt_secret: str = Field(default="your-secret-key-change-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_user_expiration: int = Field(default=7)
    jwt_refresh_expiration: int = Field(default=30)
    jwt_admin_expiration: int = Field(default=90)
    jwt_issuer: str = Field(default="E-Learning Platform")

    # Email (SMTP) Configuration
    mail_driver: str = Field(default="smtp")
    mail_host: str = Field(default="smtp.example.com")
    mail_port: int = Field(default=587)
    mail_username: str = Field(default="your@email.com")
    mail_password: str = Field(default="")
    mail_encryption: str = Field(default="tls")
    mail_from_address: str = Field(default="no-reply@example.com")
    mail_from_name: str = Field(default="E-Learning Platform")

    # File Upload Settings
    max_upload_size_mb: int = Field(default=20)
    upload_dir: str = Field(default="storage")
    allowed_file_types: List[str] = Field(
        default=["jpg", "png", "pdf", "mp4", "mp3"], env="ALLOWED_FILE_TYPES"
    )

    # Logging
    log_level: str = Field(default="info")
    log_file: str = Field(default="logs/app.log")

    # Pagination
    default_page_size: int = Field(default=10)
    max_page_size: int = Field(default=100)

    # Admin Account Defaults
    admin_default_name: str = Field(default="Super Admin")
    admin_default_email: str = Field(default="admin@example.com")
    admin_default_password: str = Field(default="Admin@123")
    admin_default_telegram_id: str = Field(default="")

    # Payment Gateway
    payment_provider: str = Field(default="fawaterk")
    payment_api_key: str = Field(default="")
    payment_currency: str = Field(default="EGP")
    payment_webhook_secret: str = Field(default="")

    # Telegram
    telegram_bot_token: str = Field(default="")
    telegram_bot_username: str = Field(default="ELearningApplicationBot")
    telegram_admin_chat_id: str = Field(default="")
    telegram_notification_enabled: bool = Field(default=False)
    telegram_channel_id: str = Field(default="elearning_channel")

    # Authentication
    authorization_enabled: bool = Field(default=True)
    authorization_roles: List[str] = Field(
        default=["admin", "teacher", "student"], env="AUTHORIZATION_ROLES"
    )
    authorization_default_role: str = Field(default="student")
    authorization_methods: List[str] = Field(
        default=["telegram", "jwt"], env="AUTHORIZATION_METHODS"
    )

    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_rate_limit: str = Field(default="20/minute", env="REDIS_RATE_LIMIT")

    # AI Service Configuration
    ai_api_key: str = Field(default="", env="AI_API_KEY")
    ai_api_endpoint: str = Field(default="", env="AI_API_ENDPOINT")
    ai_model: str = Field(default="", env="AI_MODEL")

    # Models
    verify_user_model: bool = Field(default=True, env="VERIFY_USER_MODEL")

    # --- Generic list parser ---
    @staticmethod
    def _parse_list(v, default):
        if isinstance(v, str):
            items = [item.strip() for item in v.split(",") if item.strip()]
            return items if items else default
        elif isinstance(v, list):
            return v if v else default
        return default

    @field_validator("allowed_file_types", mode="before")
    @classmethod
    def parse_file_types(cls, v):
        return cls._parse_list(v, ["jpg", "png", "pdf", "mp4", "mp3"])

    @field_validator("authorization_roles", mode="before")
    @classmethod
    def parse_auth_roles(cls, v):
        return cls._parse_list(v, ["admin", "teacher", "student"])

    @field_validator("authorization_methods", mode="before")
    @classmethod
    def parse_auth_methods(cls, v):
        return cls._parse_list(v, ["jwt"])

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        return cls._parse_list(v, ["http://localhost:3000"])

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


def load_settings():
    """Load settings with proper error handling"""
    try:
        settings = Settings()
        print("✅ Settings loaded successfully!")
        return settings
    except ValidationError as e:
        print(f"❌ Validation Error: {e}")
        print("\n📝 Error Details:")
        for error in e.errors():
            print(f"  Field: {error['loc']}")
            print(f"  Error: {error['msg']}")
            print(f"  Input: {error.get('input', 'N/A')}")
        raise
    except FileNotFoundError:
        print("⚠️  .env file not found, using default values")
        settings = Settings()
        print("✅ Settings loaded with defaults!")
        return settings
    except Exception as e:
        print(f"❌ Unexpected error loading settings: {e}")
        raise


settings = load_settings()

if __name__ == "__main__":
    settings = load_settings()

    print("\n📋 Current Configuration:")
    print("=" * 50)
    print(f"App Name: {settings.app_name}")
    print(f"Debug Mode: {settings.debug}")
    print(
        f"Database: {settings.db_connection}://{settings.db_host}:{settings.db_port}/{settings.db_database}"
    )
    print(f"Allowed File Types: {settings.allowed_file_types}")
    print(f"Authorization Roles: {settings.authorization_roles}")
    print(f"Authorization Methods: {settings.authorization_methods}")
    print(f"CORS Origins: {settings.cors_allowed_origins}")
    print(
        f"JWT Secret: {'*' * 20 if settings.jwt_secret != 'your-secret-key-change-in-production' else 'DEFAULT (CHANGE THIS!)'}"
    )
    print(
        f"Telegram Bot: {'Configured' if settings.telegram_bot_token else 'Not configured'}"
    )
    print(f"\n🔧 Environment file: {'.env' if os.path.exists('.env') else 'Not found'}")
    print("\n✨ Configuration loaded successfully!")
