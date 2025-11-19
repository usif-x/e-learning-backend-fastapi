# app/routers/community.py
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin, get_current_user, get_optional_user
from app.models.admin import Admin
from app.models.user import User
from app.schemas.community import (
    CommentCreate,
    CommentListResponse,
    CommentResponse,
    CommentUpdate,
    CommunityCreate,
    CommunityListResponse,
    CommunityMemberListResponse,
    CommunityMemberResponse,
    CommunityResponse,
    CommunityUpdate,
    JoinCommunityRequest,
    PostCreate,
    PostListResponse,
    PostResponse,
    PostUpdate,
    ReactionCreate,
    ReportedPostListResponse,
    ReportedPostResponse,
    ReportPostRequest,
    UpdateMemberRoleRequest,
)
from app.services.community import CommentService, CommunityService, PostService

router = APIRouter(
    prefix="/communities",
    tags=["Communities"],
    responses={404: {"description": "Not found"}},
)


# ==================== Admin-Only Endpoints ====================
# NOTE: These MUST be defined before parameterized routes like /{community_id}/posts/{post_id}
# to avoid route matching conflicts where "admin" is parsed as a community_id


@router.get(
    "/admin/posts/pending",
    response_model=PostListResponse,
    summary="Get pending posts (Admin)",
)
def get_pending_posts(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    community_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Get pending posts for admin review.
    Can filter by community_id.
    Admin only.
    """
    service = PostService(db)
    posts, pagination = service.get_pending_posts(page, size, community_id)
    return {"posts": posts, **pagination}


@router.post("/admin/posts/{post_id}/accept", response_model=PostResponse)
def accept_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    Accept a pending post.
    Admin only.
    """
    service = PostService(db)
    return service.accept_post(post_id, current_admin.id)


@router.post("/admin/posts/{post_id}/reject", response_model=PostResponse)
def reject_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    Reject a pending post.
    Admin only.
    """
    service = PostService(db)
    return service.reject_post(post_id, current_admin.id)


@router.get("/admin/reports", response_model=ReportedPostListResponse)
def get_reported_posts(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, pattern="^(pending|passed|deleted)$"),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    Get reported posts for admin review.
    Can filter by report status.
    Admin only.
    """
    service = PostService(db)
    reports, pagination = service.get_reported_posts(page, size, status)
    return {"reports": reports, **pagination}


@router.delete("/admin/reports/{report_id}/delete", status_code=204)
def delete_reported_post(
    report_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    Delete a reported post and mark report as deleted.
    Admin only.
    """
    service = PostService(db)
    service.delete_reported_post(report_id, current_admin.id)
    return None


@router.post("/admin/reports/{report_id}/pass", response_model=ReportedPostResponse)
def pass_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    Mark a report as passed/ignored (post is fine).
    Admin only.
    """
    service = PostService(db)
    return service.pass_report(report_id, current_admin.id)


@router.delete("/admin/posts/{post_id}", status_code=204)
def admin_delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    Admin delete a post.
    Admin only.
    """
    service = PostService(db)
    service.admin_delete_post(post_id, current_admin.id)
    return None


# ==================== Community Endpoints ====================


@router.post("/", response_model=CommunityResponse, status_code=201)
def create_community(
    community_in: CommunityCreate,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    Create a new community.
    Only admins can create communities.
    """
    service = CommunityService(db)
    return service.create_community(community_in, current_admin.id)


@router.get("/", response_model=CommunityListResponse)
def list_communities(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    is_public: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get list of communities.
    Available to all users (authenticated or not).
    Optionally filter by public/private and search by name.
    """
    service = CommunityService(db)
    user_id = current_user.id if current_user else None
    communities, pagination = service.get_communities(
        page=page, size=size, is_public=is_public, user_id=user_id, search=search
    )
    return {"communities": communities, **pagination}


@router.get("/{community_id}", response_model=CommunityResponse)
def get_community(
    community_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get a community by ID.
    Available to all users (authenticated or not).
    """
    service = CommunityService(db)
    user_id = current_user.id if current_user else None
    community = service.get_community(community_id, user_id)

    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community not found",
        )

    return community


@router.patch("/{community_id}", response_model=CommunityResponse)
def update_community(
    community_id: int,
    community_in: CommunityUpdate,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    Update a community.
    Only admins can update community settings.
    """
    service = CommunityService(db)
    community = service.update_community(community_id, community_in, current_admin.id)

    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community not found",
        )

    return community


@router.post("/{community_id}/join", response_model=CommunityMemberResponse)
def join_community(
    community_id: int,
    request: JoinCommunityRequest = None,
    invite_code: Optional[str] = Query(
        None, description="Invite code for private communities"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Join a community.
    For private communities, an invite code is required.
    Can be provided in body or as query parameter.
    """
    # Accept invite_code from either query param or request body
    code = invite_code or (request.invite_code if request else None)

    service = CommunityService(db)
    membership = service.join_community(community_id, current_user.id, code)
    return membership


@router.post("/{community_id}/leave", status_code=204)
def leave_community(
    community_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Leave a community"""
    service = CommunityService(db)
    service.leave_community(community_id, current_user.id)
    return None


@router.post("/{community_id}/upload-image", response_model=CommunityResponse)
async def upload_community_image(
    community_id: int,
    image: UploadFile = File(..., description="Community profile image"),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    Upload a community profile image.
    Only admins can upload images.
    """
    service = CommunityService(db)
    community = await service.upload_community_image(
        community_id, image, current_admin.id
    )

    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community not found",
        )

    return community


@router.post("/{community_id}/regenerate-invite", response_model=CommunityResponse)
def regenerate_invite_code(
    community_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Regenerate invite code for a private community.
    Only owners and admins can regenerate invite codes.
    This invalidates the old invite code.
    """
    service = CommunityService(db)
    community = service.regenerate_invite_code(community_id, current_user.id)

    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community not found",
        )

    return community


@router.get("/{community_id}/members", response_model=CommunityMemberListResponse)
def get_community_members(
    community_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    role: Optional[str] = Query(None, pattern="^(owner|admin|moderator|member)$"),
    search: Optional[str] = Query(
        None, description="Search by user name or telegram username"
    ),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get members of a community with pagination.
    Supports filtering by role and searching by user name/username.
    Available to all users (authenticated or not).
    """
    service = CommunityService(db)
    members, pagination = service.get_community_members(
        community_id, page, size, role, search
    )
    return {"members": members, **pagination}


# ==================== Post Endpoints ====================


@router.post("/{community_id}/posts", response_model=PostResponse, status_code=201)
def create_post(
    community_id: int,
    post_in: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new post in a community.
    Must be a member of the community to post.
    """
    service = PostService(db)
    post = service.create_post(community_id, post_in, current_user.id)
    return post


@router.get("/{community_id}/posts", response_model=PostListResponse)
def list_posts(
    community_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get posts from a community with pagination.
    Pinned posts appear first.
    """
    service = PostService(db)
    user_id = current_user.id if current_user else None
    posts, pagination = service.get_posts(community_id, page, size, user_id)
    return {"posts": posts, **pagination}


@router.get("/{community_id}/posts/{post_id}", response_model=PostResponse)
def get_post(
    community_id: int,
    post_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get a specific post from a community by ID.
    """
    service = PostService(db)
    user_id = current_user.id if current_user else None
    post = service.get_post(community_id, post_id, user_id)

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    return post


@router.patch("/posts/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    post_in: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a post.
    Only the post author can edit the post.
    """
    service = PostService(db)
    post = service.update_post(post_id, post_in, current_user.id)

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    return post


@router.delete("/posts/{post_id}", status_code=204)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a post (soft delete).
    Only the post author or community moderators can delete.
    """
    service = PostService(db)
    service.delete_post(post_id, current_user.id)
    return None


@router.post("/posts/{post_id}/media")
async def add_post_media(
    post_id: int,
    media_type: str = Query(..., regex="^(image|audio)$"),
    media_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add media (image or audio) to a post.
    Only the post author can add media.

    Supported types:
    - image: JPG, PNG, GIF, WEBP
    - audio: MP3, WAV, OGG
    """
    service = PostService(db)
    media = await service.add_post_media(
        post_id, media_file, media_type, current_user.id
    )
    return media


@router.post("/posts/{post_id}/reactions")
async def add_reaction(
    post_id: int,
    reaction_in: ReactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add or update reaction to a post.
    If the same reaction exists, it will be removed (toggle).
    """
    service = PostService(db)
    reaction = await service.add_reaction(
        post_id, current_user.id, reaction_in.reaction_type
    )

    if not reaction:
        return {"message": "Reaction removed"}

    return reaction


@router.delete("/posts/{post_id}/reactions", status_code=204)
def remove_reaction(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove user's reaction from a post"""
    service = PostService(db)
    service.remove_reaction(post_id, current_user.id)
    return None


@router.get("/posts/me", response_model=PostListResponse)
def get_my_posts(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all posts created by the current user across all communities.
    Returns posts ordered by creation date (newest first).
    """
    service = PostService(db)
    posts, pagination = service.get_user_posts(current_user.id, page, size)
    return {"posts": posts, **pagination}


# ==================== Comment Endpoints ====================


@router.post(
    "/posts/{post_id}/comments", response_model=CommentResponse, status_code=201
)
def create_comment(
    post_id: int,
    comment_in: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a comment on a post.
    Set parent_comment_id to reply to another comment.
    """
    service = CommentService(db)
    comment = service.create_comment(post_id, comment_in, current_user.id)
    return comment


@router.get("/posts/{post_id}/comments", response_model=CommentListResponse)
def list_comments(
    post_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get comments for a post with pagination.
    Returns top-level comments with nested replies.
    """
    service = CommentService(db)
    user_id = current_user.id if current_user else None
    comments, pagination = service.get_comments(post_id, page, size, user_id)
    return {"comments": comments, **pagination}


@router.patch("/comments/{comment_id}", response_model=CommentResponse)
def update_comment(
    comment_id: int,
    comment_in: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a comment.
    Only the comment author can edit.
    """
    service = CommentService(db)
    comment = service.update_comment(comment_id, comment_in, current_user.id)

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    return comment


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a comment (soft delete).
    Author or community moderators can delete.
    """
    service = CommentService(db)
    service.delete_comment(comment_id, current_user.id)
    return None


# ==================== Post Reporting Endpoints ====================


@router.post(
    "/posts/{post_id}/report", response_model=ReportedPostResponse, status_code=201
)
def report_post(
    post_id: int,
    report_in: ReportPostRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Report a post for inappropriate content.
    User must be authenticated.
    """
    service = PostService(db)
    return service.report_post(post_id, current_user.id, report_in.reason)
