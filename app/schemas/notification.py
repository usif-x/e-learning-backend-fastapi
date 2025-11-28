from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NotificationBase(BaseModel):
    title: str = Field(..., max_length=200)
    message: str
    type: str = Field(default="info")
    is_active: bool = Field(default=True)


class NotificationCreate(NotificationBase):
    pass


class NotificationUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    type: Optional[str] = None
    is_active: Optional[bool] = None


class NotificationResponse(NotificationBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
