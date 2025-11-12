from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
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
    description="Create a new admin",
    status_code=201,
)
async def create_admin(admin: CreateAdmin, db: Session = Depends(get_db)):
    return admin_service.create(admin, db)
