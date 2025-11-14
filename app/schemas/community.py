# app/schemas/community.py
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

# ==================== Community Schemas ====================


class CommunityBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    is_public: bool = True
    allow_member_posts: bool = True
    require_approval: bool = False


class CommunityCreate(CommunityBase):
    pass


class CommunityUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = None
    image: Optional[str] = None
    is_public: Optional[bool] = None
    allow_member_posts: Optional[bool] = None
    require_approval: Optional[bool] = None
    is_active: Optional[bool] = None


class CommunityMemberInfo(BaseModel):
    """Minimal user info for community members"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    profile_picture: Optional[str]
    telegram_username: Optional[str]


class CommunityResponse(CommunityBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image: Optional[str]
    invite_code: Optional[str]
    is_active: bool
    members_count: int
    posts_count: int
    created_at: datetime
    updated_at: datetime

    # User's membership info (if they're a member)
    user_role: Optional[str] = None
    is_member: bool = False


class CommunityListResponse(BaseModel):
    communities: List[CommunityResponse]
    total: int
    page: int
    size: int
    total_pages: int


# ==================== Community Member Schemas ====================


class CommunityMemberBase(BaseModel):
    role: str = Field(default="member", pattern="^(owner|admin|moderator|member)$")


class CommunityMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    community_id: int
    user_id: int
    role: str
    joined_via: str
    joined_at: datetime

    # User info
    user: CommunityMemberInfo


class JoinCommunityRequest(BaseModel):
    invite_code: Optional[str] = None


class UpdateMemberRoleRequest(BaseModel):
    role: str = Field(..., pattern="^(admin|moderator|member)$")


# ==================== Post Schemas ====================


class PostBase(BaseModel):
    content: Optional[str] = Field(None, max_length=10000)


class PostCreate(PostBase):
    pass


class PostUpdate(BaseModel):
    content: Optional[str] = Field(None, max_length=10000)


class PostMediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    media_type: str
    media_url: str
    file_size: Optional[int]
    duration: Optional[int]
    position: int
    created_at: datetime


class PostAuthorInfo(BaseModel):
    """Minimal user info for post author"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    profile_picture: Optional[str]
    telegram_username: Optional[str]


class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    community_id: int
    user_id: int
    is_pinned: bool
    is_edited: bool
    reactions_count: int
    comments_count: int
    created_at: datetime
    updated_at: datetime
    edited_at: Optional[datetime]

    # Related data
    author: PostAuthorInfo
    media: List[PostMediaResponse] = []

    # User interaction status
    user_reaction: Optional[str] = None


class PostListResponse(BaseModel):
    posts: List[PostResponse]
    total: int
    page: int
    size: int
    total_pages: int


# ==================== Reaction Schemas ====================


class ReactionCreate(BaseModel):
    reaction_type: str = Field(default="like", pattern="^(like|love|laugh|sad|angry)$")


class ReactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    user_id: int
    reaction_type: str
    created_at: datetime

    user: CommunityMemberInfo


# ==================== Comment Schemas ====================


class CommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class CommentCreate(CommentBase):
    parent_comment_id: Optional[int] = None


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class CommentResponse(CommentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    user_id: int
    parent_comment_id: Optional[int]
    is_edited: bool
    reactions_count: int
    created_at: datetime
    updated_at: datetime
    edited_at: Optional[datetime]

    # Related data
    author: PostAuthorInfo
    replies: List["CommentResponse"] = []


class CommentListResponse(BaseModel):
    comments: List[CommentResponse]
    total: int
    page: int
    size: int
