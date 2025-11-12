# app/schemas/user.py

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class Admin(BaseModel):
    id: int
    name: str
    username: str
    email: str
    level: int
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class AdminResponse(Admin):
    pass


class CreateAdmin(BaseModel):
    name: str
    username: str
    email: str
    password: str
    level: int
    is_verified: bool


class CreateAdminResponse(BaseModel):
    message: str
    admin: AdminResponse


class ListOfAdminsResponse(BaseModel):
    admins: List[AdminResponse]
    total: str
    page: str
    next: str
    prev: str


class UpdateAdmin(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    level: Optional[int] = None
    is_verified: Optional[bool] = None
