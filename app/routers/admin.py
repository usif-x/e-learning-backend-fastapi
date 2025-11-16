from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin, require_admin_level
from app.models.admin import Admin
from app.schemas.admin import AdminResponse, CreateAdmin, CreateAdminResponse
from app.services.admin import AdminServices

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    responses={404: {"description": "Not found"}},
)

admin_service = AdminServices()


@router.post(
    "/create",
    response_model=CreateAdminResponse,
    description="Create a new admin (requires super admin - level 999)",
    status_code=201,
)
async def create_admin(
    admin_data: CreateAdmin,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin_level(999)),
):
    """
    Create a new admin account. Only super admins (level 999) can create new admins.
    """
    return admin_service.create(admin_data, db)


@router.get(
    "/me",
    response_model=AdminResponse,
    description="Get current admin profile",
)
async def get_current_admin_profile(
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Get the current authenticated admin's profile information.
    """
    return AdminResponse(
        id=current_admin.id,
        name=current_admin.name,
        username=current_admin.username,
        email=current_admin.email,
        telegram_id=current_admin.telegram_id,
        level=current_admin.level,
        is_verified=current_admin.is_verified,
        created_at=current_admin.created_at,
        updated_at=current_admin.updated_at,
    )
