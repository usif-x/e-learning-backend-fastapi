# app/services/user_service.py

from decimal import Decimal, InvalidOperation
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

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
