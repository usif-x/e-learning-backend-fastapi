from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.core.decorator import db_exception
from app.core.hasher import PasswordHelper
from app.models.admin import Admin
from app.schemas.admin import AdminResponse, CreateAdmin, CreateAdminResponse


class AdminServices:

    def __init__(self):
        pass

    @db_exception
    def create(self, admin: CreateAdmin, db: Session) -> CreateAdminResponse:
        new_admin = Admin(
            **admin.model_dump(exclude={"password"}),
            password=PasswordHelper.hash_password(admin.password),
        )
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        return CreateAdminResponse(
            message="Admin created successfully, you can now login.",
            admin=AdminResponse.model_validate(new_admin),
        )
