# app/models/relations.py

from sqlalchemy.orm import relationship

# Import all relevant models
from .comment import Comment
from .community import Community
from .community_member import CommunityMember
from .post import Post
from .post_media import PostMedia
from .post_reaction import PostReaction
from .reported_post import ReportedPost
from .user import User


def setup_relationships():
    """
    Configure all SQLAlchemy relationships between models.
    """

    # --- Community System Relationships ---

    # 1. Community to Members (One-to-Many)
    Community.members = relationship(
        "CommunityMember",
        back_populates="community",
        cascade="all, delete-orphan",
    )
    CommunityMember.community = relationship("Community", back_populates="members")

    # 2. User to Community Memberships (One-to-Many)
    User.community_memberships = relationship(
        "CommunityMember",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    CommunityMember.user = relationship("User", back_populates="community_memberships")

    # 3. Direct Many-to-Many: User <-> Community (for convenience)
    User.communities = relationship(
        "Community",
        secondary="community_members",
        back_populates="users",
        viewonly=True,
    )
    Community.users = relationship(
        "User",
        secondary="community_members",
        back_populates="communities",
        viewonly=True,
    )

    # 4. Community to Posts (One-to-Many)
    Community.posts = relationship(
        "Post",
        back_populates="community",
        cascade="all, delete-orphan",
        order_by="Post.created_at.desc()",
    )
    Post.community = relationship("Community", back_populates="posts")

    # 5. User to Posts (One-to-Many)
    User.posts = relationship(
        "Post",
        back_populates="author",
        cascade="all, delete-orphan",
    )
    Post.author = relationship("User", back_populates="posts")

    # 6. Post to Media (One-to-Many)
    Post.media = relationship(
        "PostMedia",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="PostMedia.position",
    )
    PostMedia.post = relationship("Post", back_populates="media")

    # 7. Post to Reactions (One-to-Many)
    Post.reactions = relationship(
        "PostReaction",
        back_populates="post",
        cascade="all, delete-orphan",
    )
    PostReaction.post = relationship("Post", back_populates="reactions")

    # 8. User to Reactions (One-to-Many)
    User.post_reactions = relationship(
        "PostReaction",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    PostReaction.user = relationship("User", back_populates="post_reactions")

    # 9. Post to Comments (One-to-Many)
    Post.comments = relationship(
        "Comment",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="Comment.created_at",
    )
    Comment.post = relationship("Post", back_populates="comments")

    # 10. User to Comments (One-to-Many)
    User.comments = relationship(
        "Comment",
        back_populates="author",
        cascade="all, delete-orphan",
    )
    Comment.author = relationship("User", back_populates="comments")

    # 11. Comment self-referential (for replies)
    Comment.parent = relationship(
        "Comment",
        remote_side=[Comment.id],
        backref="replies",
    )

    # 12. Post to ReportedPosts (One-to-Many)
    Post.reports = relationship(
        "ReportedPost",
        back_populates="post",
        cascade="all, delete-orphan",
    )
    ReportedPost.post = relationship("Post", back_populates="reports")

    # 13. User to ReportedPosts (One-to-Many) - as reporter
    User.reported_posts = relationship(
        "ReportedPost",
        back_populates="reporter",
        cascade="all, delete-orphan",
        foreign_keys="ReportedPost.reporter_id",
    )
    ReportedPost.reporter = relationship(
        "User",
        back_populates="reported_posts",
        foreign_keys="ReportedPost.reporter_id",
    )
