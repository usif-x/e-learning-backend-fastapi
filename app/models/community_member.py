# app/models/community_member.py
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class CommunityMember(Base):
    __tablename__ = "community_members"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    community_id = Column(
        Integer, ForeignKey("communities.id"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=True, index=True)

    # Role in community
    role = Column(
        String(20), default="member", nullable=False
    )  # 'owner', 'admin', 'moderator', 'member'

    # Join metadata
    joined_via = Column(
        String(20), default="direct", nullable=False
    )  # 'direct', 'invite_link', 'approval'

    # Timestamps
    joined_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Unique constraint: one user/admin can only be a member once per community
    __table_args__ = (
        UniqueConstraint(
            "community_id", "user_id", name="unique_community_user_member"
        ),
        UniqueConstraint(
            "community_id", "admin_id", name="unique_community_admin_member"
        ),
    )

    def __repr__(self):
        return f"<CommunityMember(community_id={self.community_id}, user_id={self.user_id}, role='{self.role}')>"
