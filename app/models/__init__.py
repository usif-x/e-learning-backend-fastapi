"""
Models package initialization
Import all models and setup relationships
"""

from .admin import Admin
from .comment import Comment
from .community import Community
from .community_member import CommunityMember
from .post import Post
from .post_media import PostMedia
from .post_reaction import PostReaction

# Import and setup relationships
from .relations import setup_relationships
from .reported_post import ReportedPost
from .user import User

# Setup all relationships after models are imported
setup_relationships()

# Make models available at package level
__all__ = [
    "Admin",
    "Comment",
    "Community",
    "CommunityMember",
    "Post",
    "PostMedia",
    "PostReaction",
    "ReportedPost",
    "User",
]
