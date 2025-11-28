from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationUpdate


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self, notification_in: NotificationCreate, admin_id: int
    ) -> Notification:
        notification = Notification(**notification_in.model_dump(), created_by=admin_id)
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def list(self, skip: int = 0, limit: int = 20) -> List[Notification]:
        return (
            self.db.query(Notification)
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get(self, notification_id: int) -> Optional[Notification]:
        return (
            self.db.query(Notification)
            .filter(Notification.id == notification_id)
            .first()
        )

    def update(
        self, notification_id: int, notification_in: NotificationUpdate
    ) -> Optional[Notification]:
        notification = self.get(notification_id)
        if not notification:
            return None
        for field, value in notification_in.model_dump(exclude_unset=True).items():
            setattr(notification, field, value)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def delete(self, notification_id: int) -> bool:
        notification = self.get(notification_id)
        if not notification:
            return False
        self.db.delete(notification)
        self.db.commit()
        return True

    def get_user_notifications(
        self, skip: int = 0, limit: int = 20, type: Optional[str] = None
    ) -> List[Notification]:
        query = self.db.query(Notification).filter(
            Notification.is_active == True,
        )
        if type:
            query = query.filter(Notification.type == type)
        return (
            query.order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
