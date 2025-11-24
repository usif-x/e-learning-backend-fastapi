# app/services/user_service.py

import random
import string
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.hasher import PasswordHelper
from app.models.user import User
from app.utils.tg_service import TelegramService


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_user(self, user_id: int) -> Optional[User]:
        """
        Retrieves a single user by their ID.
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def add_funds_to_wallet(self, user_id: int, amount: float) -> bool:
        """
        Adds a specified amount to the user's wallet.
        Returns True if the addition was successful, False otherwise.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        try:
            dec_amount = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            return False

        if dec_amount <= 0:
            return False

        user.wallet_balance += dec_amount
        self.db.commit()
        return True

    def update_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> bool:
        """
        Update user's password after verifying current password.
        Returns True if password was updated successfully, False otherwise.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # Check if user has a password set (some users might only use telegram auth)
        if not user.hashed_password:
            return False

        # Verify current password
        if not PasswordHelper.check_password(current_password, user.hashed_password):
            return False

        # Hash new password and update
        user.hashed_password = PasswordHelper.hash_password(new_password)
        self.db.commit()
        return True

    def get_user_profile(self, user_id: int) -> Optional[User]:
        """
        Get detailed user profile information.
        """
        return self.db.query(User).filter(User.id == user_id).first()

    async def initiate_password_reset(self, phone_number: str) -> bool:
        """
        Initiate password reset by sending verification code to user's Telegram.
        Returns True if code was sent successfully, False otherwise.
        """
        # Find user by phone_number
        user = self.db.query(User).filter(User.phone_number == phone_number).first()

        if not user:
            return False

        # Check if user has a password set (some users might only use telegram auth)
        if not user.hashed_password:
            return False

        # Check if user has telegram_id for sending verification code
        if not user.telegram_id:
            return False

        # Generate 6-digit verification code
        reset_code = "".join(random.choices(string.digits, k=6))

        # Set expiry time (15 minutes from now)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        print(
            f"DEBUG: Generated reset code {reset_code} for phone {phone_number}, expires at {expires_at}"
        )

        # Store code and expiry
        user.reset_code = reset_code
        user.reset_code_expires_at = expires_at
        self.db.commit()

        # Send code via Telegram
        try:
            tg_service = TelegramService(bot_token=settings.telegram_bot_token)
            message = f"""🔐 كود إعادة تعيين كلمة المرور

كود التحقق الخاص بك: `{reset_code}`

هذا الكود صالح لمدة 15 دقيقة فقط.
إذا لم تقم بطلب هذا الكود، يرجى تجاهل هذه الرسالة."""

            result = await tg_service.send_message(
                chat_id=str(user.telegram_id), text=message, parse_mode="Markdown"
            )

            if result:
                return True
            else:
                # Clean up the code if sending failed
                user.reset_code = None
                user.reset_code_expires_at = None
                self.db.commit()
                return False

        except Exception as e:
            # Clean up the code if sending failed
            user.reset_code = None
            user.reset_code_expires_at = None
            self.db.commit()
            print(f"Failed to send password reset code: {e}")
            return False

    def verify_reset_code(self, phone_number: str, code: str) -> bool:
        """
        Verify the password reset code.
        Returns True if code is valid and not expired, False otherwise.
        """
        # Find user by phone_number
        user = self.db.query(User).filter(User.phone_number == phone_number).first()

        if not user:
            print(f"DEBUG: User not found with phone number: {phone_number}")
            return False

        print(f"DEBUG: Found user {user.id} with phone {phone_number}")
        print(
            f"DEBUG: User reset_code: {user.reset_code}, expires_at: {user.reset_code_expires_at}"
        )
        print(f"DEBUG: Provided code: {code}")
        print(f"DEBUG: Current time: {datetime.now(timezone.utc)}")

        # Check if code matches and hasn't expired
        if (
            user.reset_code == code
            and user.reset_code_expires_at
            and datetime.now(timezone.utc) <= user.reset_code_expires_at
        ):
            print("DEBUG: Code verification successful")
            return True

        print("DEBUG: Code verification failed")
        return False

    def reset_password(self, phone_number: str, code: str, new_password: str) -> bool:
        """
        Reset password using verification code.
        Returns True if password was reset successfully, False otherwise.
        """
        # First verify the code
        if not self.verify_reset_code(phone_number, code):
            return False

        # Find user
        user = self.db.query(User).filter(User.phone_number == phone_number).first()

        if not user:
            return False

        # Update password
        user.hashed_password = PasswordHelper.hash_password(new_password)

        # Clear reset code
        user.reset_code = None
        user.reset_code_expires_at = None

        self.db.commit()
        return True

    # User Management Methods (for admin use)

    def get_all_users(
        self, page: int = 1, per_page: int = 20, search: Optional[str] = None
    ) -> dict:
        """
        Get paginated list of all users with optional search.
        Returns dict with users list and pagination info.
        """
        query = self.db.query(User)

        # Apply search filter if provided
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                or_(
                    User.full_name.ilike(search_filter),
                    User.email.ilike(search_filter),
                    User.phone_number.ilike(search_filter),
                    User.telegram_username.ilike(search_filter),
                    User.telegram_id.ilike(search_filter),
                )
            )

        # Get total count
        total = query.count()

        # Apply pagination
        users = (
            query.order_by(User.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        # Calculate pagination info
        total_pages = (total + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1

        return {
            "users": users,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev,
            "next_page": page + 1 if has_next else None,
            "prev_page": page - 1 if has_prev else None,
        }

    def update_user(self, user_id: int, update_data: dict) -> Optional[User]:
        """
        Update user information.
        Returns updated user if successful, None if user not found.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        # Update fields if provided
        for field, value in update_data.items():
            if value is not None:
                setattr(user, field, value)

        user.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user_status(self, user_id: int, status: str) -> Optional[User]:
        """
        Update user status.
        Returns updated user if successful, None if user not found.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        user.status = status
        user.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)
        return user

    def activate_deactivate_user(self, user_id: int, is_active: bool) -> Optional[User]:
        """
        Activate or deactivate user account.
        Returns updated user if successful, None if user not found.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        user.is_active = is_active
        user.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user permanently.
        Returns True if user was deleted, False if user not found.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        self.db.delete(user)
        self.db.commit()
        return True
