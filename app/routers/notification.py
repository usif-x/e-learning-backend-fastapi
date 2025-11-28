from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin, get_current_user
from app.models.admin import Admin
from app.models.user import User
from app.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    NotificationUpdate,
)
from app.services.notification import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# Admin CRUD endpoints
@router.post("/", response_model=NotificationResponse)
def create_notification(
    notification_in: NotificationCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    service = NotificationService(db)
    notification = service.create(notification_in, current_admin.id)
    return notification


@router.get("/", response_model=List[NotificationResponse])
def list_notifications(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    service = NotificationService(db)
    notifications = service.list(skip, limit)
    return notifications


@router.get("/user", response_model=List[NotificationResponse])
def get_user_notifications(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
    type: Optional[str] = None,
):
    service = NotificationService(db)
    notifications = service.get_user_notifications(skip, limit, type)
    return notifications


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    service = NotificationService(db)
    notification = service.get(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.patch("/{notification_id}", response_model=NotificationResponse)
def update_notification(
    notification_id: int,
    notification_in: NotificationUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    service = NotificationService(db)
    notification = service.update(notification_id, notification_in)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.delete("/{notification_id}", status_code=204)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    service = NotificationService(db)
    success = service.delete(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return None


# User GET endpoint
