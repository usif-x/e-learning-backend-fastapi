"""
Chat Service
Service layer for RAG-based teaching chat system
"""

import logging
from typing import List, Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.chat_session import ChatMessage, ChatSession
from app.schemas.chat import (
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionCreateFromPDF,
    ChatSessionDetail,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatSessionUpdate,
)
from app.utils.ai import ai_service

logger = logging.getLogger(__name__)


class ChatService:
    """Service for managing chat sessions and RAG-based teaching interactions"""

    @staticmethod
    async def create_session_from_text(
        db: Session,
        user_id: int,
        session_data: ChatSessionCreate,
    ) -> ChatSessionResponse:
        """
        Create a new chat session with text content

        Args:
            db: Database session
            user_id: ID of the user creating the session
            session_data: Session creation data with content

        Returns:
            Created chat session
        """
        # Create the session
        chat_session = ChatSession(
            user_id=user_id,
            title=session_data.title,
            content=session_data.content,
            language=session_data.language,
        )

        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)

        # Create initial AI greeting message
        await ChatService._create_initial_greeting(db, chat_session)

        return ChatService._to_session_response(chat_session)

    @staticmethod
    async def create_session_from_pdf(
        db: Session,
        user_id: int,
        session_data: ChatSessionCreateFromPDF,
        pdf_file: UploadFile,
    ) -> ChatSessionResponse:
        """
        Create a new chat session from PDF file

        Args:
            db: Database session
            user_id: ID of the user creating the session
            session_data: Session creation data
            pdf_file: Uploaded PDF file

        Returns:
            Created chat session
        """
        # Extract text from PDF
        try:
            pdf_content = await ai_service.extract_text_from_pdf(pdf_file)
        except Exception as e:
            logger.error(f"Failed to extract PDF content: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process PDF file: {str(e)}",
            )

        # Create the session with extracted content
        chat_session = ChatSession(
            user_id=user_id,
            title=session_data.title,
            content=pdf_content,
            language=session_data.language,
        )

        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)

        # Create initial AI greeting message
        await ChatService._create_initial_greeting(db, chat_session)

        return ChatService._to_session_response(chat_session)

    @staticmethod
    async def _create_initial_greeting(db: Session, chat_session: ChatSession):
        """
        Create the initial AI greeting message for a new chat session

        Args:
            db: Database session
            chat_session: The chat session
        """
        # Get user for personalization
        from app.models.user import User

        user = db.query(User).filter(User.id == chat_session.user_id).first()
        user_name = user.full_name if user and user.full_name else None

        # Generate initial greeting using AI
        greeting = await ai_service.generate_teaching_greeting(
            content_preview=chat_session.content[:1000],
            language=chat_session.language,
            user_name=user_name,
        )

        # Create the greeting message
        greeting_message = ChatMessage(
            session_id=chat_session.id,
            role="assistant",
            content=greeting,
        )

        db.add(greeting_message)
        db.commit()

    @staticmethod
    def get_session(
        db: Session,
        session_id: int,
        user_id: int,
    ) -> ChatSessionDetail:
        """
        Get a chat session with all messages

        Args:
            db: Database session
            session_id: ID of the chat session
            user_id: ID of the user (for authorization)

        Returns:
            Chat session with messages

        Raises:
            HTTPException: If session not found or unauthorized
        """
        chat_session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )

        if not chat_session:
            raise HTTPException(
                status_code=404,
                detail="Chat session not found",
            )

        # Build detail response
        return ChatSessionDetail(
            id=chat_session.id,
            user_id=chat_session.user_id,
            title=chat_session.title,
            language=chat_session.language,
            is_active=chat_session.is_active,
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at,
            message_count=len(chat_session.messages),
            messages=[
                ChatService._to_message_response(msg) for msg in chat_session.messages
            ],
            content_preview=chat_session.content[:500] if chat_session.content else "",
        )

    @staticmethod
    def list_sessions(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        active_only: bool = False,
    ) -> ChatSessionListResponse:
        """
        List all chat sessions for a user

        Args:
            db: Database session
            user_id: ID of the user
            page: Page number (1-indexed)
            page_size: Items per page
            active_only: Whether to return only active sessions

        Returns:
            Paginated list of chat sessions
        """
        # Build query
        query = db.query(ChatSession).filter(ChatSession.user_id == user_id)

        if active_only:
            query = query.filter(ChatSession.is_active == True)

        # Get total count
        total = query.count()

        # Get paginated sessions
        sessions = (
            query.order_by(ChatSession.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size

        return ChatSessionListResponse(
            sessions=[ChatService._to_session_response(s) for s in sessions],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    async def send_message(
        db: Session,
        session_id: int,
        user_id: int,
        message_content: str,
    ) -> tuple[ChatMessageResponse, ChatMessageResponse]:
        """
        Send a message in a chat session and get AI response

        Args:
            db: Database session
            session_id: ID of the chat session
            user_id: ID of the user
            message_content: The user's message

        Returns:
            Tuple of (user_message, assistant_message)

        Raises:
            HTTPException: If session not found or unauthorized
        """
        # Get the chat session with user
        from app.models.user import User

        chat_session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )

        if not chat_session:
            raise HTTPException(
                status_code=404,
                detail="Chat session not found",
            )

        if not chat_session.is_active:
            raise HTTPException(
                status_code=400,
                detail="Chat session is not active",
            )

        # Get user for personalization
        user = db.query(User).filter(User.id == user_id).first()
        user_name = user.full_name if user and user.full_name else None

        # Create user message
        user_message = ChatMessage(
            session_id=session_id,
            role="user",
            content=message_content,
        )

        db.add(user_message)
        db.commit()
        db.refresh(user_message)

        # Get conversation history
        history = [
            {"role": msg.role, "content": msg.content} for msg in chat_session.messages
        ]

        # Generate AI response using RAG
        try:
            ai_response = await ai_service.generate_teaching_response(
                user_message=message_content,
                source_content=chat_session.content,
                conversation_history=history,
                language=chat_session.language,
                user_name=user_name,
            )
        except Exception as e:
            logger.error(f"Failed to generate AI response: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate response: {str(e)}",
            )

        # Create assistant message
        assistant_message = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=ai_response,
        )

        db.add(assistant_message)

        # Update session's updated_at timestamp
        chat_session.updated_at = func.now()

        db.commit()
        db.refresh(assistant_message)

        return (
            ChatService._to_message_response(user_message),
            ChatService._to_message_response(assistant_message),
        )

    @staticmethod
    async def send_message_stream(
        db: Session,
        session_id: int,
        user_id: int,
        message_content: str,
    ):
        """
        Send a message in a chat session and stream AI response

        Args:
            db: Database session
            session_id: ID of the chat session
            user_id: ID of the user
            message_content: The user's message

        Yields:
            Dictionary chunks with type and data for SSE streaming

        Raises:
            HTTPException: If session not found or unauthorized
        """
        # Get the chat session with user
        from app.models.user import User

        chat_session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )

        if not chat_session:
            raise HTTPException(
                status_code=404,
                detail="Chat session not found",
            )

        if not chat_session.is_active:
            raise HTTPException(
                status_code=400,
                detail="Chat session is not active",
            )

        # Get user for personalization
        user = db.query(User).filter(User.id == user_id).first()
        user_name = user.full_name if user and user.full_name else None

        # Create user message
        user_message = ChatMessage(
            session_id=session_id,
            role="user",
            content=message_content,
        )

        db.add(user_message)
        db.commit()
        db.refresh(user_message)

        # Send user message event
        yield {
            "type": "user_message",
            "message": ChatService._to_message_response(user_message).model_dump(
                mode="json"
            ),
        }

        # Get conversation history
        history = [
            {"role": msg.role, "content": msg.content} for msg in chat_session.messages
        ]

        # Stream AI response using RAG
        full_response = ""
        try:
            async for chunk in ai_service.generate_teaching_response_stream(
                user_message=message_content,
                source_content=chat_session.content,
                conversation_history=history,
                language=chat_session.language,
                user_name=user_name,
            ):
                full_response += chunk
                # Send content chunk
                yield {"type": "content", "content": chunk}

        except Exception as e:
            logger.error(f"Failed to stream AI response: {str(e)}")
            yield {"type": "error", "error": str(e)}
            return

        # Save complete assistant message to database
        assistant_message = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=full_response,
        )

        db.add(assistant_message)

        # Update session's updated_at timestamp
        chat_session.updated_at = func.now()

        db.commit()
        db.refresh(assistant_message)

        # Send done event with complete message
        yield {
            "type": "done",
            "message": ChatService._to_message_response(assistant_message).model_dump(
                mode="json"
            ),
        }

    @staticmethod
    def update_session(
        db: Session,
        session_id: int,
        user_id: int,
        update_data: ChatSessionUpdate,
    ) -> ChatSessionResponse:
        """
        Update a chat session

        Args:
            db: Database session
            session_id: ID of the chat session
            user_id: ID of the user
            update_data: Update data

        Returns:
            Updated chat session

        Raises:
            HTTPException: If session not found or unauthorized
        """
        chat_session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )

        if not chat_session:
            raise HTTPException(
                status_code=404,
                detail="Chat session not found",
            )

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(chat_session, field, value)

        db.commit()
        db.refresh(chat_session)

        return ChatService._to_session_response(chat_session)

    @staticmethod
    def delete_session(
        db: Session,
        session_id: int,
        user_id: int,
    ) -> None:
        """
        Delete a chat session

        Args:
            db: Database session
            session_id: ID of the chat session
            user_id: ID of the user

        Raises:
            HTTPException: If session not found or unauthorized
        """
        chat_session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )

        if not chat_session:
            raise HTTPException(
                status_code=404,
                detail="Chat session not found",
            )

        db.delete(chat_session)
        db.commit()

    @staticmethod
    def get_messages(
        db: Session,
        session_id: int,
        user_id: int,
        limit: Optional[int] = None,
    ) -> List[ChatMessageResponse]:
        """
        Get messages from a chat session

        Args:
            db: Database session
            session_id: ID of the chat session
            user_id: ID of the user
            limit: Optional limit on number of messages

        Returns:
            List of chat messages

        Raises:
            HTTPException: If session not found or unauthorized
        """
        # Verify session ownership
        chat_session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )

        if not chat_session:
            raise HTTPException(
                status_code=404,
                detail="Chat session not found",
            )

        # Get messages
        query = db.query(ChatMessage).filter(ChatMessage.session_id == session_id)

        if limit:
            query = query.order_by(ChatMessage.created_at.desc()).limit(limit)
            messages = query.all()
            messages.reverse()  # Return in chronological order
        else:
            messages = query.order_by(ChatMessage.created_at.asc()).all()

        return [ChatService._to_message_response(msg) for msg in messages]

    # ============================================
    # Helper Methods
    # ============================================

    @staticmethod
    def _to_session_response(session: ChatSession) -> ChatSessionResponse:
        """Convert ChatSession to ChatSessionResponse"""
        return ChatSessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            language=session.language,
            is_active=session.is_active,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(session.messages) if session.messages else 0,
        )

    @staticmethod
    def _to_message_response(message: ChatMessage) -> ChatMessageResponse:
        """Convert ChatMessage to ChatMessageResponse"""
        return ChatMessageResponse(
            id=message.id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
        )


# Create singleton instance
chat_service = ChatService()
