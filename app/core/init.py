"""
Application initialization module
Handles initial setup tasks like creating default super admin
"""

import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.hasher import PasswordHelper
from app.models.admin import Admin

logger = logging.getLogger(__name__)


def init_super_admin(db: Session) -> None:
    """
    Initialize super admin user if it doesn't exist.

    Checks if any admin exists in the database. If not, creates a super admin
    using credentials from settings (config.py).

    Args:
        db: Database session
    """
    try:
        # Check if any admin exists
        existing_admin = db.query(Admin).first()

        if existing_admin:
            logger.info(
                f"✅ Admin user already exists (ID: {existing_admin.id}, Username: {existing_admin.username})"
            )
            return

        # Create super admin
        super_admin = Admin(
            name=settings.admin_default_name,
            username="admin",  # Default username
            email=settings.admin_default_email,
            password=PasswordHelper.hash_password(settings.admin_default_password),
            is_verified=True,
            level=999,  # Super admin level
        )

        db.add(super_admin)
        db.commit()
        db.refresh(super_admin)

        logger.info("=" * 60)
        logger.info("🎉 SUPER ADMIN CREATED SUCCESSFULLY!")
        logger.info("=" * 60)
        logger.info(f"Username: admin")
        logger.info(f"Email: {settings.admin_default_email}")
        logger.info(f"Password: {settings.admin_default_password}")
        logger.info(f"Level: {super_admin.level}")
        logger.info("=" * 60)
        logger.warning("⚠️  IMPORTANT: Change the default password immediately!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Failed to initialize super admin: {e}")
        db.rollback()
        raise


def initialize_application(db: Session) -> None:
    """
    Run all application initialization tasks.

    Args:
        db: Database session
    """
    logger.info("🚀 Starting application initialization...")

    # Initialize super admin
    init_super_admin(db)

    # Add other initialization tasks here
    # Example: init_default_categories(db)
    # Example: init_default_settings(db)

    logger.info("✅ Application initialization completed!")
