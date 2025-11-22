from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.core.decorator import db_exception
from app.core.hasher import PasswordHelper
from app.models.admin import Admin
from app.schemas.admin import (
    AdminResponse,
    CreateAdmin,
    CreateAdminResponse,
    ListOfAdminsResponse,
    UpdateAdmin,
)


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

    @db_exception
    def get_all_admins(
        self, db: Session, page: int = 1, limit: int = 10
    ) -> ListOfAdminsResponse:
        offset = (page - 1) * limit
        admins_query = db.query(Admin).offset(offset).limit(limit).all()
        total_admins = db.query(Admin).count()

        admins = [AdminResponse.model_validate(admin) for admin in admins_query]

        total_pages = (total_admins + limit - 1) // limit
        next_page = page + 1 if page < total_pages else None
        prev_page = page - 1 if page > 1 else None

        return ListOfAdminsResponse(
            admins=admins,
            total=str(total_admins),
            page=str(page),
            next=str(next_page) if next_page else None,
            prev=str(prev_page) if prev_page else None,
        )

    @db_exception
    def get_admin_by_id(self, admin_id: int, db: Session) -> AdminResponse:
        admin = db.query(Admin).filter(Admin.id == admin_id).first()
        if not admin:
            raise HTTPException(status_code=404, detail="Admin not found")
        return AdminResponse.model_validate(admin)

    @db_exception
    def update_admin(
        self, admin_id: int, update_data: UpdateAdmin, db: Session
    ) -> AdminResponse:
        admin = db.query(Admin).filter(Admin.id == admin_id).first()
        if not admin:
            raise HTTPException(status_code=404, detail="Admin not found")

        update_dict = update_data.model_dump(exclude_unset=True)

        # Hash password if it's being updated
        if "password" in update_dict:
            update_dict["password"] = PasswordHelper.hash_password(
                update_dict["password"]
            )

        for key, value in update_dict.items():
            setattr(admin, key, value)

        db.commit()
        db.refresh(admin)
        return AdminResponse.model_validate(admin)

    @db_exception
    def delete_admin(self, admin_id: int, db: Session) -> dict:
        admin = db.query(Admin).filter(Admin.id == admin_id).first()
        if not admin:
            raise HTTPException(status_code=404, detail="Admin not found")

        # Prevent deletion of super admins
        if admin.level >= 999:
            raise HTTPException(
                status_code=403, detail="Cannot delete super admin accounts"
            )

        db.delete(admin)
        db.commit()
        return {"message": "Admin deleted successfully"}

    @db_exception
    def reset_admin_password(
        self, admin_id: int, new_password: str, db: Session
    ) -> dict:
        admin = db.query(Admin).filter(Admin.id == admin_id).first()
        if not admin:
            raise HTTPException(status_code=404, detail="Admin not found")

        admin.password = PasswordHelper.hash_password(new_password)
        db.commit()
        return {"message": "Admin password reset successfully"}
