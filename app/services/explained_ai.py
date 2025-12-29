# app/services/explained_ai.py

import secrets
from typing import Optional

from sqlalchemy.orm import Session

from app.models.explained_ai import ExplainedAI
from app.models.user import User


class ExplainedAIService:
    def __init__(self, db: Session):
        self.db = db

    def create_explained_content(
        self, user_id: int, source: str, content: str
    ) -> ExplainedAI:
        """
        Create a new explained content entry.
        Checks for existing entry with same user_id and source.
        """
        # Check if already exists
        existing = self.get_by_user_and_source(user_id, source)
        if existing:
            # Update existing
            existing.content = content
            existing.updated_at = None  # Will be auto-updated
            self.db.commit()
            self.db.refresh(existing)
            return existing

        # Create new
        explained_ai = ExplainedAI(
            user_id=user_id,
            source=source,
            content=content,
        )
        self.db.add(explained_ai)
        self.db.commit()
        self.db.refresh(explained_ai)
        return explained_ai

    def get_by_user_and_source(
        self, user_id: int, source: str
    ) -> Optional[ExplainedAI]:
        """Get explained content by user and source."""
        return (
            self.db.query(ExplainedAI)
            .filter(ExplainedAI.user_id == user_id, ExplainedAI.source == source)
            .first()
        )

    def get_by_id(self, explained_id: int) -> Optional[ExplainedAI]:
        """Get explained content by ID."""
        return self.db.query(ExplainedAI).filter(ExplainedAI.id == explained_id).first()

    def get_by_share_link(self, share_link: str) -> Optional[ExplainedAI]:
        """Get explained content by share link (for public access)."""
        return (
            self.db.query(ExplainedAI)
            .filter(ExplainedAI.share_link == share_link, ExplainedAI.is_shared == True)
            .first()
        )

    def generate_share_link(self, explained_id: int) -> Optional[str]:
        """Generate a unique share link for the explained content."""
        explained = self.get_by_id(explained_id)
        if not explained:
            return None

        # Generate unique link
        share_link = secrets.token_urlsafe(16)
        while self.get_by_share_link(share_link):
            share_link = secrets.token_urlsafe(16)

        explained.share_link = share_link
        explained.is_shared = True
        self.db.commit()
        self.db.refresh(explained)
        return share_link

    def get_user_explained_content(self, user_id: int) -> list[ExplainedAI]:
        """Get all explained content for a user."""
        return (
            self.db.query(ExplainedAI)
            .filter(ExplainedAI.user_id == user_id)
            .order_by(ExplainedAI.created_at.desc())
            .all()
        )

    def delete_explained_content(self, explained_id: int, user_id: int) -> bool:
        """Delete explained content (only by owner)."""
        explained = (
            self.db.query(ExplainedAI)
            .filter(ExplainedAI.id == explained_id, ExplainedAI.user_id == user_id)
            .first()
        )
        if not explained:
            return False

        self.db.delete(explained)
        self.db.commit()
        return True
