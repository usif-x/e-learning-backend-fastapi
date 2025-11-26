from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin, require_admin_level
from app.models.admin import Admin
from app.schemas.admin import (
    AdminResponse,
    CreateAdmin,
    CreateAdminResponse,
    ListOfAdminsResponse,
    UpdateAdmin,
)
from app.schemas.user import (
    ListUsersResponse,
    UpdateUserRequest,
    UpdateUserStatusRequest,
    UserActivationRequest,
    UserManagementResponse,
)
from app.services.admin import AdminServices
from app.services.user import UserService

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
    return AdminResponse.model_validate(current_admin)


@router.get(
    "/list",
    response_model=ListOfAdminsResponse,
    description="List all admins (requires super admin - level 999)",
)
async def list_admins(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin_level(999)),
):
    """
    Get a paginated list of all admins. Only super admins can access this endpoint.
    """
    return admin_service.get_all_admins(db, page, limit)


# ==================== User Management Endpoints ====================


@router.get(
    "/users",
    response_model=ListUsersResponse,
    description="List all users with pagination and search (requires admin access)",
)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(
        None, description="Search query for name, email, phone, or telegram info"
    ),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Get a paginated list of all users with optional search functionality.
    Requires admin access.
    """
    user_service = UserService(db)
    result = user_service.get_all_users(page=page, per_page=per_page, search=search)

    return {
        "users": result["users"],
        "total": result["total"],
        "page": result["page"],
        "per_page": result["per_page"],
        "total_pages": result["total_pages"],
        "has_next": result["has_next"],
        "has_prev": result["has_prev"],
        "next_page": result["next_page"],
        "prev_page": result["prev_page"],
    }


@router.get(
    "/users/{user_id}",
    response_model=UserManagementResponse,
    description="Get user by ID (requires admin access)",
)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Get a specific user by ID. Requires admin access.
    """
    user_service = UserService(db)
    user = user_service.get_user(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.put(
    "/users/{user_id}",
    response_model=UserManagementResponse,
    description="Update user information (requires admin access)",
)
async def update_user(
    user_id: int,
    user_data: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Update user information. Requires admin access.
    """
    user_service = UserService(db)
    update_data = user_data.model_dump(exclude_unset=True)

    user = user_service.update_user(user_id, update_data)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.put(
    "/users/{user_id}/status",
    response_model=UserManagementResponse,
    description="Update user status (requires admin access)",
)
async def update_user_status(
    user_id: int,
    status_data: UpdateUserStatusRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Update user status (student, teacher, admin, blocked, pending).
    Requires admin access.
    """
    user_service = UserService(db)
    user = user_service.update_user_status(user_id, status_data.status)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.put(
    "/users/{user_id}/activation",
    response_model=UserManagementResponse,
    description="Activate or deactivate user account (requires admin access)",
)
async def activate_deactivate_user(
    user_id: int,
    activation_data: UserActivationRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Activate or deactivate a user account. Requires admin access.
    """
    user_service = UserService(db)
    user = user_service.activate_deactivate_user(user_id, activation_data.is_active)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.delete(
    "/users/{user_id}",
    description="Delete user permanently (requires super admin - level 999)",
    status_code=200,
)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin_level(999)),
):
    """
    Delete a user permanently. Requires super admin level (999).
    """
    user_service = UserService(db)
    success = user_service.delete_user(user_id)

    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "User deleted successfully"}


# ==================== Admin Management Endpoints ====================


@router.get(
    "/{admin_id}",
    response_model=AdminResponse,
    description="Get admin by ID (requires super admin - level 999)",
)
async def get_admin(
    admin_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin_level(999)),
):
    """
    Get a specific admin by ID. Only super admins can access this endpoint.
    """
    return admin_service.get_admin_by_id(admin_id, db)


@router.put(
    "/{admin_id}",
    response_model=AdminResponse,
    description="Update admin details",
)
async def update_admin(
    admin_id: int,
    admin_data: UpdateAdmin,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Update admin details. Super admins can update any admin, regular admins can only update their own profile.
    """
    # Check permissions: super admin can update anyone, regular admin can only update self
    if current_admin.level < 999 and current_admin.id != admin_id:
        raise HTTPException(
            status_code=403, detail="You can only update your own profile"
        )

    # Prevent regular admins from changing their own level or verification status
    if current_admin.level < 999:
        if admin_data.level is not None:
            raise HTTPException(
                status_code=403, detail="You cannot change admin levels"
            )
        if admin_data.is_verified is not None:
            raise HTTPException(
                status_code=403, detail="You cannot change verification status"
            )

    return admin_service.update_admin(admin_id, admin_data, db)


@router.delete(
    "/{admin_id}",
    description="Delete admin (requires super admin - level 999)",
    status_code=200,
)
async def delete_admin(
    admin_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin_level(999)),
):
    """
    Delete an admin account. Only super admins can delete admins.
    Cannot delete super admin accounts.
    """
    # Prevent self-deletion
    if current_admin.id == admin_id:
        raise HTTPException(
            status_code=400, detail="You cannot delete your own account"
        )

    return admin_service.delete_admin(admin_id, db)


@router.post(
    "/{admin_id}/reset-password",
    description="Reset admin password (requires super admin - level 999)",
    status_code=200,
)
async def reset_admin_password(
    admin_id: int,
    new_password: str = Query(..., min_length=4, description="New password"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin_level(999)),
):
    """
    Reset an admin's password. Only super admins can reset passwords.
    """
    return admin_service.reset_admin_password(admin_id, new_password, db)
