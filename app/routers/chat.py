"""
Chat Router
API endpoints for RAG-based teaching chat system
"""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.chat import (
    ChatMessageResponse,
    ChatSendMessageRequest,
    ChatSendMessageResponse,
    ChatSessionCreate,
    ChatSessionCreateFromPDF,
    ChatSessionDetail,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatSessionUpdate,
)
from app.services.chat import chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat - RAG Teaching System"])


# ============================================
# Chat Session Management Endpoints
# ============================================


@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=201,
    summary="Create chat session from text",
    description="Create a new RAG-based teaching chat session with text content",
)
async def create_chat_session(
    session_data: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new chat session with text content.

    The AI will act as a teacher and start an interactive learning session
    based on the provided content.
    """
    return await chat_service.create_session_from_text(
        db=db,
        user_id=current_user.id,
        session_data=session_data,
    )


@router.post(
    "/sessions/from-pdf",
    response_model=ChatSessionResponse,
    status_code=201,
    summary="Create chat session from PDF",
    description="Create a new RAG-based teaching chat session from PDF file",
)
async def create_chat_session_from_pdf(
    title: str = Form(..., min_length=1, max_length=255),
    language: str = Form(default="en", pattern="^(en|ar)$"),
    session_type: str = Form(default="asking", pattern="^(asking|explaining)$"),
    pdf_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new chat session by uploading a PDF file.

    The PDF content will be extracted and the AI will start an interactive
    teaching session based on the content.

    - **title**: Title for the chat session
    - **language**: Preferred language for the chat (en or ar)
    - **session_type**: Type of session - 'asking' (AI asks questions) or 'explaining' (AI explains content)
    - **pdf_file**: The PDF file to extract content from
    """
    # Validate file type
    if not pdf_file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted",
        )

    logger.info(
        f"[PDF Session Create] Form data received - session_type: '{session_type}'"
    )

    session_data = ChatSessionCreateFromPDF(
        title=title,
        language=language,
        session_type=session_type,
    )

    logger.info(
        f"[PDF Session Create] Schema validated - session_type: '{session_data.session_type}'"
    )

    result = await chat_service.create_session_from_pdf(
        db=db,
        user_id=current_user.id,
        session_data=session_data,
        pdf_file=pdf_file,
    )
    logger.info(
        f"[PDF Session Create] Response will send - session_type: '{result.session_type}'"
    )
    return result


@router.get(
    "/sessions",
    response_model=ChatSessionListResponse,
    summary="List chat sessions",
    description="Get a paginated list of user's chat sessions",
)
def list_chat_sessions(
    page: int = 1,
    page_size: int = 20,
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a list of all chat sessions for the current user.

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **active_only**: Show only active sessions (default: false)
    """
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be >= 1")

    if page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=400, detail="Page size must be between 1 and 100"
        )

    return chat_service.list_sessions(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        active_only=active_only,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionDetail,
    summary="Get chat session details",
    description="Get a specific chat session with all messages",
)
def get_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed information about a specific chat session including
    all messages in the conversation.
    """
    return chat_service.get_session(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
    )


@router.patch(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
    summary="Update chat session",
    description="Update chat session properties",
)
def patch_chat_session(
    session_id: int,
    update_data: ChatSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a chat session's properties like title, language, or active status.
    """
    return chat_service.update_session(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
        update_data=update_data,
    )


@router.put(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
    summary="Update chat session",
    description="Update chat session properties",
)
def put_chat_session(
    session_id: int,
    update_data: ChatSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a chat session's properties like title, language, or active status.
    """
    return chat_service.update_session(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
        update_data=update_data,
    )


@router.delete(
    "/sessions/{session_id}",
    status_code=204,
    summary="Delete chat session",
    description="Delete a chat session and all its messages",
)
def delete_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a chat session permanently. This will also delete all
    associated messages.
    """
    chat_service.delete_session(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
    )
    return None


# ============================================
# Chat Interaction Endpoints
# ============================================


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatSendMessageResponse,
    summary="Send message in chat",
    description="Send a message and receive AI teacher's response",
)
async def send_chat_message(
    session_id: int,
    message_data: ChatSendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a message in a chat session and receive the AI teacher's response.

    The AI will:
    - Answer questions based on the source content
    - Ask follow-up questions to test understanding
    - Explain concepts when the user doesn't know the answer
    - Provide guidance on whether to continue or review specific topics
    """
    user_msg, assistant_msg = await chat_service.send_message(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
        message_content=message_data.message,
    )

    return ChatSendMessageResponse(
        user_message=user_msg,
        assistant_message=assistant_msg,
    )


@router.post(
    "/sessions/{session_id}/messages/stream",
    summary="Send message with streaming response",
    description="Send a message and receive AI teacher's response as a stream (SSE)",
)
async def send_chat_message_stream(
    session_id: int,
    message_data: ChatSendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a message in a chat session and receive the AI teacher's response as a stream.

    This endpoint uses Server-Sent Events (SSE) to stream the response in real-time,
    creating a more interactive chat experience.

    The response format is SSE with the following event types:
    - `user_message`: The user's message that was saved
    - `content`: Chunks of the AI response as they're generated
    - `done`: Final message with the complete assistant message
    - `error`: Error information if something goes wrong

    Example client usage (JavaScript):
    ```javascript
    const eventSource = new EventSource('/chat/sessions/1/messages/stream');

    eventSource.addEventListener('user_message', (e) => {
      const data = JSON.parse(e.data);
      console.log('User said:', data.content);
    });

    eventSource.addEventListener('content', (e) => {
      const chunk = JSON.parse(e.data);
      // Append chunk to UI in real-time
      appendToChat(chunk.content);
    });

    eventSource.addEventListener('done', (e) => {
      const data = JSON.parse(e.data);
      console.log('Complete message:', data.message);
      eventSource.close();
    });
    ```
    """

    async def event_generator():
        try:
            # Generate streaming response
            async for data in chat_service.send_message_stream(
                db=db,
                session_id=session_id,
                user_id=current_user.id,
                message_content=message_data.message,
            ):
                # Yield SSE formatted data
                yield f"data: {json.dumps(data)}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            error_data = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        },
    )


@router.get(
    "/sessions/{session_id}/messages",
    response_model=List[ChatMessageResponse],
    summary="Get chat messages",
    description="Get messages from a chat session",
)
def get_chat_messages(
    session_id: int,
    limit: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all messages from a chat session.

    - **limit**: Optional limit on number of most recent messages to return
    """
    if limit is not None and limit < 1:
        raise HTTPException(status_code=400, detail="Limit must be >= 1")

    return chat_service.get_messages(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
        limit=limit,
    )
