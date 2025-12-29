# app/schemas/explained_ai.py

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ExplainedAIBase(BaseModel):
    source: str
    content: str
    is_shared: bool = False


class ExplainedAICreate(ExplainedAIBase):
    pass


class ExplainedAIUpdate(BaseModel):
    content: Optional[str] = None
    is_shared: Optional[bool] = None


class ExplainedAIResponse(ExplainedAIBase):
    id: int
    user_id: int
    share_link: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExplainedAIShareResponse(BaseModel):
    """Response for shared explained content (public access)"""

    id: int
    source: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
