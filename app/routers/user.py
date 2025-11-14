# app/routers/users.py

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from httpx import get
from sqlalchemy.orm import Session

from app.core.database import get_db

# Import the specific schemas we need
from app.schemas.user import UserResponse
from app.services.user import UserService

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a single user by their ID.
    """
    service = UserService(db)
    db_user = service.get_user(user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.post("/{user_id}/charge-wallet")
def charge_user_wallet(user_id: int, amount: float, db: Session = Depends(get_db)):
    """
    Charge (add funds to) a user's wallet.
    """
    service = UserService(db)
    success = service.add_funds_to_wallet(user_id=user_id, amount=amount)
    if not success:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    return {"message": "Wallet charged successfully"}
