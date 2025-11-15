"""
Models package initialization
Import all models and setup relationships
"""

from .admin import Admin
from .category import Category
from .comment import Comment
from .community import Community
from .community_member import CommunityMember
from .course import Course
from .lecture import Lecture
from .lecture_content import LectureContent
from .post import Post
from .post_media import PostMedia
from .post_reaction import PostReaction
from .quiz_attempt import QuizAttempt

# Import and setup relationships
from .relations import setup_relationships
from .reported_post import ReportedPost
from .user import User

# Setup all relationships after models are imported
setup_relationships()

# Make models available at package level
__all__ = [
    "Admin",
    "Category",
    "Comment",
    "Community",
    "CommunityMember",
    "Course",
    "Lecture",
    "LectureContent",
    "Post",
    "PostMedia",
    "PostReaction",
    "QuizAttempt",
    "ReportedPost",
    "User",
]
