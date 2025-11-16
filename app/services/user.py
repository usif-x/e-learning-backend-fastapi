# app/services/user_service.py

from decimal import Decimal, InvalidOperation
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.core.hasher import PasswordHelper
from app.models.user import User


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
