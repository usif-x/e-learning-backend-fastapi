"""
Chat Session Schemas
Schemas for RAG-based teaching chat system
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# ============================================
# Chat Message Schemas
# ============================================


class ChatMessageBase(BaseModel):
    """Base schema for chat messages"""

    content: str = Field(..., min_length=1, max_length=10000)


class ChatMessageCreate(ChatMessageBase):
    """Schema for creating a chat message"""

    pass


class ChatMessageResponse(ChatMessageBase):
    """Schema for chat message response"""

    id: int
    session_id: int
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Chat Session Schemas
# ============================================


class ChatSessionBase(BaseModel):
    """Base schema for chat sessions"""

    title: str = Field(..., min_length=1, max_length=255)
    language: str = Field(default="en", pattern="^(en|ar)$")
    session_type: str = Field(default="asking", pattern="^(asking|explaining)$")


class ChatSessionCreate(ChatSessionBase):
    """Schema for creating a chat session with text content"""

    content: str = Field(
        ..., min_length=10, description="The source content for the chat session"
    )


class ChatSessionCreateFromPDF(ChatSessionBase):
    """Schema for creating a chat session from PDF - file is uploaded separately"""

    pass


class ChatSessionUpdate(BaseModel):
    """Schema for updating a chat session"""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    language: Optional[str] = Field(None, pattern="^(en|ar)$")
    session_type: Optional[str] = Field(None, pattern="^(asking|explaining)$")
    is_active: Optional[bool] = None


class ChatSessionResponse(ChatSessionBase):
    """Schema for chat session response"""

    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    message_count: int = Field(
        default=0, description="Number of messages in this session"
    )

    class Config:
        from_attributes = True


class ChatSessionDetail(ChatSessionResponse):
    """Schema for detailed chat session with messages"""

    messages: List[ChatMessageResponse] = []
    content_preview: str = Field(default="", description="First 500 chars of content")

    class Config:
        from_attributes = True


# ============================================
# Chat Interaction Schemas
# ============================================


class ChatSendMessageRequest(BaseModel):
    """Schema for sending a message in a chat session"""

    message: str = Field(..., min_length=1, max_length=10000)


class ChatSendMessageResponse(BaseModel):
    """Schema for chat message exchange response"""

    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse


# ============================================
# Chat Session List Schemas
# ============================================


class ChatSessionListResponse(BaseModel):
    """Schema for paginated chat session list"""

    sessions: List[ChatSessionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
