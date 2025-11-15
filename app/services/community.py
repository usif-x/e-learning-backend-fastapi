# app/services/community.py
import math
import secrets
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, selectinload

from app.models.comment import Comment
from app.models.community import Community
from app.models.community_member import CommunityMember
from app.models.post import Post
from app.models.post_media import PostMedia
from app.models.post_reaction import PostReaction
from app.models.reported_post import ReportedPost
from app.models.user import User
from app.schemas.community import (
    CommunityCreate,
    CommunityUpdate,
    PostCreate,
    PostUpdate,
)
from app.utils.file_upload import file_upload_service


class CommunityService:
    def __init__(self, db: Session):
        self.db = db

    def generate_invite_code(self) -> str:
        """Generate a unique invite code for private communities"""
        while True:
            code = secrets.token_urlsafe(16)
            existing = (
                self.db.query(Community).filter(Community.invite_code == code).first()
            )
            if not existing:
                return code

    def create_community(
        self, community_in: CommunityCreate, admin_id: int
    ) -> Community:
        """Create a new community (admin only)"""
        # Create community
        community = Community(
            **community_in.model_dump(),
            invite_code=(
                self.generate_invite_code() if not community_in.is_public else None
            ),
            members_count=0,  # Will increment after adding admin
        )

        self.db.add(community)
        self.db.flush()  # Get the ID

        # Add the admin who created the community as the first member
        membership = CommunityMember(
            community_id=community.id,
            admin_id=admin_id,
            user_id=None,
            role="member",
            joined_via="direct",
        )
        self.db.add(membership)

        # Update member count
        community.members_count = 1

        self.db.commit()
        self.db.refresh(community)

        return community

    def get_community(
        self, community_id: int, user_id: Optional[int] = None
    ) -> Optional[Community]:
        """Get a community by ID with user membership info"""
        community = (
            self.db.query(Community).filter(Community.id == community_id).first()
        )

        if not community:
            return None

        # Add user membership info
        if user_id:
            membership = (
                self.db.query(CommunityMember)
                .filter(
                    and_(
                        CommunityMember.community_id == community_id,
                        CommunityMember.user_id == user_id,
                    )
                )
                .first()
            )
            community.user_role = membership.role if membership else None
            community.is_member = membership is not None

        return community

    def get_communities(
        self,
        page: int = 1,
        size: int = 20,
        is_public: Optional[bool] = None,
        user_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Community], dict]:
        """Get list of communities with pagination"""
        query = self.db.query(Community).filter(Community.is_active == True)

        # Filter by public/private
        if is_public is not None:
            query = query.filter(Community.is_public == is_public)

        # Search by name or description
        if search:
            query = query.filter(
                or_(
                    Community.name.ilike(f"%{search}%"),
                    Community.description.ilike(f"%{search}%"),
                )
            )

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * size
        communities = (
            query.order_by(Community.created_at.desc()).offset(offset).limit(size).all()
        )

        # Add user membership info
        if user_id:
            for community in communities:
                membership = (
                    self.db.query(CommunityMember)
                    .filter(
                        and_(
                            CommunityMember.community_id == community.id,
                            CommunityMember.user_id == user_id,
                        )
                    )
                    .first()
                )
                community.user_role = membership.role if membership else None
                community.is_member = membership is not None

        # Pagination metadata
        total_pages = math.ceil(total / size)
        pagination = {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
        }

        return communities, pagination

    def update_community(
        self, community_id: int, community_in: CommunityUpdate, admin_id: int
    ) -> Optional[Community]:
        """Update a community (admin only)"""
        community = (
            self.db.query(Community).filter(Community.id == community_id).first()
        )
        if not community:
            return None

        # Update fields
        for field, value in community_in.model_dump(exclude_unset=True).items():
            setattr(community, field, value)

        self.db.commit()
        self.db.refresh(community)

        return community

    def join_community(
        self, community_id: int, user_id: int, invite_code: Optional[str] = None
    ) -> CommunityMember:
        """Join a community"""
        community = (
            self.db.query(Community).filter(Community.id == community_id).first()
        )
        if not community:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Community not found",
            )

        if not community.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Community is not active",
            )

        # Check if already a member
        existing = (
            self.db.query(CommunityMember)
            .filter(
                and_(
                    CommunityMember.community_id == community_id,
                    CommunityMember.user_id == user_id,
                )
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already a member of this community",
            )

        # Check access permissions
        joined_via = "direct"
        if not community.is_public:
            if not invite_code or invite_code != community.invite_code:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid invite code for private community",
                )
            joined_via = "invite_link"

        # Create membership
        membership = CommunityMember(
            community_id=community_id,
            user_id=user_id,
            role="member",
            joined_via=joined_via,
        )

        self.db.add(membership)

        # Update members count
        community.members_count += 1

        self.db.commit()
        self.db.refresh(membership)

        return membership

    def leave_community(self, community_id: int, user_id: int) -> bool:
        """Leave a community"""
        membership = (
            self.db.query(CommunityMember)
            .filter(
                and_(
                    CommunityMember.community_id == community_id,
                    CommunityMember.user_id == user_id,
                )
            )
            .first()
        )

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not a member of this community",
            )

        if membership.role == "owner":
            # Check if there are other members
            members_count = (
                self.db.query(CommunityMember)
                .filter(CommunityMember.community_id == community_id)
                .count()
            )

            if members_count > 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Owner must transfer ownership or remove all members before leaving",
                )

        # Delete membership
        self.db.delete(membership)

        # Update members count
        community = (
            self.db.query(Community).filter(Community.id == community_id).first()
        )
        if community:
            community.members_count -= 1

        self.db.commit()

        return True

    async def upload_community_image(
        self, community_id: int, image_file: UploadFile, admin_id: int
    ) -> Optional[Community]:
        """Upload community profile image (admin only)"""
        community = (
            self.db.query(Community).filter(Community.id == community_id).first()
        )
        if not community:
            return None

        # Delete old image if exists
        if community.image:
            file_upload_service.delete_image(community.image)

        # Save new image
        uuid_filename, relative_path = await file_upload_service.save_image(
            image_file, folder="communities"
        )

        community.image = relative_path
        self.db.commit()
        self.db.refresh(community)

        return community

    def regenerate_invite_code(
        self, community_id: int, admin_id: int
    ) -> Optional[Community]:
        """Regenerate invite code for a private community (admin only)"""
        community = (
            self.db.query(Community).filter(Community.id == community_id).first()
        )
        if not community:
            return None

        # Check if community is private
        if community.is_public:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot generate invite code for public communities",
            )

        # Generate new invite code
        community.invite_code = self.generate_invite_code()
        self.db.commit()
        self.db.refresh(community)

        return community

    def get_community_members(
        self,
        community_id: int,
        page: int = 1,
        size: int = 20,
        role: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[CommunityMember], dict]:
        """Get members of a community with pagination.

        - `role`: optional filter by role (owner/admin/moderator/member)
        - `search`: optional case-insensitive search against user's full_name or telegram_username
        Returns a tuple of (members_list, pagination_dict)
        """
        query = (
            self.db.query(CommunityMember)
            .filter(CommunityMember.community_id == community_id)
            .options(selectinload(CommunityMember.user))
        )

        # Filter by role if provided
        if role:
            query = query.filter(CommunityMember.role == role)

        # Search by user name or telegram username
        if search:
            # Join with User to filter on user fields
            query = query.join(User).filter(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    User.telegram_username.ilike(f"%{search}%"),
                )
            )

        # Total count for pagination
        total = query.count()

        # Apply pagination
        offset = (page - 1) * size
        members = (
            query.order_by(CommunityMember.joined_at.asc())
            .offset(offset)
            .limit(size)
            .all()
        )

        # Pagination metadata
        total_pages = math.ceil(total / size) if size > 0 else 0
        pagination = {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
        }

        return members, pagination


class PostService:
    def __init__(self, db: Session):
        self.db = db

    def create_post(self, community_id: int, post_in: PostCreate, user_id: int) -> Post:
        """Create a new post in a community"""
        # Check if user is a member
        membership = (
            self.db.query(CommunityMember)
            .filter(
                and_(
                    CommunityMember.community_id == community_id,
                    CommunityMember.user_id == user_id,
                )
            )
            .first()
        )

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Must be a member to post in this community",
            )

        # Check community settings
        community = (
            self.db.query(Community).filter(Community.id == community_id).first()
        )
        if not community or not community.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Community not found or inactive",
            )

        if not community.allow_member_posts and membership.role not in [
            "owner",
            "admin",
            "moderator",
        ]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only moderators and admins can post in this community",
            )

        # Create post
        post = Post(
            community_id=community_id,
            user_id=user_id,
            content=post_in.content,
            post_status=(
                "pending" if not community.auto_accept_posts else "accepted"
            ),  # All posts start as pending or accepted based on community setting
        )

        self.db.add(post)

        # Don't update community posts count yet - only count accepted posts
        # community.posts_count += 1

        self.db.commit()
        self.db.refresh(post)

        return post

    def get_posts(
        self,
        community_id: int,
        page: int = 1,
        size: int = 20,
        user_id: Optional[int] = None,
    ) -> Tuple[List[Post], dict]:
        """Get posts from a community with pagination (only accepted posts)"""
        query = (
            self.db.query(Post)
            .filter(
                and_(
                    Post.community_id == community_id,
                    Post.is_deleted == False,
                    Post.post_status == "accepted",  # Only show accepted posts
                )
            )
            .options(
                selectinload(Post.author),
                selectinload(Post.media),
            )
        )

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * size
        posts = (
            query.order_by(Post.is_pinned.desc(), Post.created_at.desc())
            .offset(offset)
            .limit(size)
            .all()
        )

        # Add user reaction info
        if user_id:
            for post in posts:
                reaction = (
                    self.db.query(PostReaction)
                    .filter(
                        and_(
                            PostReaction.post_id == post.id,
                            PostReaction.user_id == user_id,
                        )
                    )
                    .first()
                )
                post.user_reaction = reaction.reaction_type if reaction else None

        # Pagination metadata
        total_pages = math.ceil(total / size)
        pagination = {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
        }

        return posts, pagination

    def get_post(
        self,
        community_id: int,
        post_id: int,
        user_id: Optional[int] = None,
    ) -> Optional[Post]:
        """Get a specific post from a community by ID (only accepted posts)"""
        post = (
            self.db.query(Post)
            .filter(
                and_(
                    Post.id == post_id,
                    Post.community_id == community_id,
                    Post.is_deleted == False,
                    Post.post_status == "accepted",  # Only show accepted posts
                )
            )
            .options(
                selectinload(Post.author),
                selectinload(Post.media),
            )
            .first()
        )

        if not post:
            return None

        # Add user reaction info
        if user_id:
            reaction = (
                self.db.query(PostReaction)
                .filter(
                    and_(
                        PostReaction.post_id == post.id,
                        PostReaction.user_id == user_id,
                    )
                )
                .first()
            )
            post.user_reaction = reaction.reaction_type if reaction else None

        return post

    def get_user_posts(
        self,
        user_id: int,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Post], dict]:
        """Get all posts created by a specific user across all communities (only accepted posts)"""
        query = (
            self.db.query(Post)
            .filter(
                and_(
                    Post.user_id == user_id,
                    Post.is_deleted == False,
                    Post.post_status == "accepted",  # Only show accepted posts
                )
            )
            .options(
                selectinload(Post.author),
                selectinload(Post.media),
                selectinload(Post.community),
            )
        )

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * size
        posts = query.order_by(Post.created_at.desc()).offset(offset).limit(size).all()

        # Add user reaction info (user always sees their own reactions)
        for post in posts:
            reaction = (
                self.db.query(PostReaction)
                .filter(
                    and_(
                        PostReaction.post_id == post.id,
                        PostReaction.user_id == user_id,
                    )
                )
                .first()
            )
            post.user_reaction = reaction.reaction_type if reaction else None

        # Pagination metadata
        total_pages = math.ceil(total / size)
        pagination = {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
        }

        return posts, pagination

    def update_post(
        self, post_id: int, post_in: PostUpdate, user_id: int
    ) -> Optional[Post]:
        """Update a post"""
        post = self.db.query(Post).filter(Post.id == post_id).first()
        if not post:
            return None

        # Check if user is the author
        if post.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the post author can edit this post",
            )

        # Update content
        if post_in.content is not None:
            post.content = post_in.content
            post.is_edited = True
            post.edited_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(post)

        return post

    def delete_post(self, post_id: int, user_id: int) -> bool:
        """Delete a post (soft delete)"""
        post = (
            self.db.query(Post)
            .filter(Post.id == post_id)
            .options(selectinload(Post.community))
            .first()
        )

        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )

        # Check if user is the author or a moderator/admin
        is_author = post.user_id == user_id

        membership = (
            self.db.query(CommunityMember)
            .filter(
                and_(
                    CommunityMember.community_id == post.community_id,
                    CommunityMember.user_id == user_id,
                    CommunityMember.role.in_(["owner", "admin", "moderator"]),
                )
            )
            .first()
        )

        if not is_author and not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the post author or moderators can delete this post",
            )

        # Soft delete
        post.is_deleted = True

        # Update community posts count
        if post.community:
            post.community.posts_count = max(0, post.community.posts_count - 1)

        self.db.commit()

        return True

    def admin_delete_post(self, post_id: int, admin_id: int) -> bool:
        """Admin delete a post (soft delete)"""
        post = (
            self.db.query(Post)
            .filter(Post.id == post_id)
            .options(selectinload(Post.community))
            .first()
        )
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )
        # Soft delete
        self.db.delete(post)
        self.db.flush()

        # Update community posts count
        if post.community:
            post.community.posts_count = max(0, post.community.posts_count - 1)

        self.db.commit()

        return True

    async def add_post_media(
        self, post_id: int, media_file: UploadFile, media_type: str, user_id: int
    ) -> PostMedia:
        """Add media (image/audio) to a post"""
        post = self.db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )

        # Check if user is the author
        if post.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the post author can add media",
            )

        # Get current media count for position
        media_count = (
            self.db.query(PostMedia).filter(PostMedia.post_id == post_id).count()
        )

        # Get file size before saving
        file_content = await media_file.read()
        file_size = len(file_content)
        await media_file.seek(0)  # Reset file pointer

        # Save media file using the appropriate method for the media type
        uuid_filename, relative_path = await file_upload_service.save_media(
            media_file, media_type=media_type, folder="posts"
        )

        # Create media record
        post_media = PostMedia(
            post_id=post_id,
            media_type=media_type,
            media_url=relative_path,
            file_size=file_size,
            position=media_count,
        )

        self.db.add(post_media)
        self.db.commit()
        self.db.refresh(post_media)

        return post_media

    def add_reaction(
        self, post_id: int, user_id: int, reaction_type: str = "like"
    ) -> PostReaction:
        """Add or update reaction to a post"""
        post = self.db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )

        # Check if reaction already exists
        existing = (
            self.db.query(PostReaction)
            .filter(
                and_(
                    PostReaction.post_id == post_id,
                    PostReaction.user_id == user_id,
                )
            )
            .first()
        )

        if existing:
            # Update reaction type
            if existing.reaction_type == reaction_type:
                # Remove reaction if same type
                self.db.delete(existing)
                post.reactions_count = max(0, post.reactions_count - 1)
                self.db.commit()
                return None
            else:
                existing.reaction_type = reaction_type
                self.db.commit()
                self.db.refresh(existing)
                return existing
        else:
            # Create new reaction
            reaction = PostReaction(
                post_id=post_id,
                user_id=user_id,
                reaction_type=reaction_type,
            )

            self.db.add(reaction)
            post.reactions_count += 1

            self.db.commit()
            self.db.refresh(reaction)

            return reaction

    def remove_reaction(self, post_id: int, user_id: int) -> bool:
        """Remove user's reaction from a post"""
        reaction = (
            self.db.query(PostReaction)
            .filter(
                and_(
                    PostReaction.post_id == post_id,
                    PostReaction.user_id == user_id,
                )
            )
            .first()
        )

        if not reaction:
            return False

        # Update post reactions count
        post = self.db.query(Post).filter(Post.id == post_id).first()
        if post:
            post.reactions_count = max(0, post.reactions_count - 1)

        self.db.delete(reaction)
        self.db.commit()

        return True

    # ==================== Post Moderation Methods ====================

    def get_pending_posts(
        self,
        page: int = 1,
        size: int = 20,
        community_id: Optional[int] = None,
    ) -> Tuple[List[Post], dict]:
        """Get pending posts for admin review"""
        query = (
            self.db.query(Post)
            .filter(
                and_(
                    Post.post_status == "pending",
                    Post.is_deleted == False,
                )
            )
            .options(
                selectinload(Post.author),
                selectinload(Post.community),
                selectinload(Post.media),
            )
        )

        # Filter by community if specified
        if community_id:
            query = query.filter(Post.community_id == community_id)

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * size
        posts = query.order_by(Post.created_at.asc()).offset(offset).limit(size).all()

        # Pagination metadata
        total_pages = math.ceil(total / size)
        pagination = {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
        }

        return posts, pagination

    def accept_post(self, post_id: int, admin_id: int) -> Optional[Post]:
        """Accept a pending post (admin only)"""
        post = self.db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )

        if post.post_status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Post is already {post.post_status}",
            )

        # Update post status
        post.post_status = "accepted"

        # Increment community posts count
        community = (
            self.db.query(Community).filter(Community.id == post.community_id).first()
        )
        if community:
            community.posts_count += 1

        self.db.commit()
        self.db.refresh(post)

        return post

    def reject_post(self, post_id: int, admin_id: int) -> Optional[Post]:
        """Reject a pending post (admin only)"""
        post = self.db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )

        if post.post_status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Post is already {post.post_status}",
            )

        # Update post status
        post.post_status = "rejected"

        self.db.commit()
        self.db.refresh(post)

        return post

    # ==================== Post Reporting Methods ====================

    def report_post(self, post_id: int, user_id: int, reason: str) -> ReportedPost:
        """Report a post"""
        # Check if post exists
        post = self.db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )

        # Check if user already reported this post
        existing_report = (
            self.db.query(ReportedPost)
            .filter(
                and_(
                    ReportedPost.post_id == post_id,
                    ReportedPost.reporter_id == user_id,
                    ReportedPost.report_status == "pending",
                )
            )
            .first()
        )

        if existing_report:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reported this post",
            )

        # Create report
        report = ReportedPost(
            post_id=post_id,
            reporter_id=user_id,
            reason=reason,
            report_status="pending",
        )

        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        return report

    def get_reported_posts(
        self,
        page: int = 1,
        size: int = 20,
        report_status: Optional[str] = None,
    ) -> Tuple[List[ReportedPost], dict]:
        """Get reported posts for admin review"""
        query = self.db.query(ReportedPost).options(
            selectinload(ReportedPost.post).selectinload(Post.author),
            selectinload(ReportedPost.post).selectinload(Post.community),
            selectinload(ReportedPost.reporter),
        )

        # Filter by status if specified
        if report_status:
            query = query.filter(ReportedPost.report_status == report_status)

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * size
        reports = (
            query.order_by(ReportedPost.created_at.desc())
            .offset(offset)
            .limit(size)
            .all()
        )

        # Pagination metadata
        total_pages = math.ceil(total / size)
        pagination = {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
        }

        return reports, pagination

    def delete_reported_post(self, report_id: int, admin_id: int) -> bool:
        """Delete a reported post and mark report as deleted (admin only)"""
        report = (
            self.db.query(ReportedPost).filter(ReportedPost.id == report_id).first()
        )
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found",
            )

        # Get the post
        post = self.db.query(Post).filter(Post.id == report.post_id).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )

        # Soft delete the post
        post.is_deleted = True

        # Update community posts count if post was accepted
        if post.post_status == "accepted":
            community = (
                self.db.query(Community)
                .filter(Community.id == post.community_id)
                .first()
            )
            if community:
                community.posts_count = max(0, community.posts_count - 1)

        # Update report status
        report.report_status = "deleted"
        report.reviewed_by = admin_id
        report.reviewed_at = datetime.utcnow()

        self.db.commit()

        return True

    def pass_report(self, report_id: int, admin_id: int) -> ReportedPost:
        """Mark a report as passed/ignored (admin only)"""
        report = (
            self.db.query(ReportedPost).filter(ReportedPost.id == report_id).first()
        )
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found",
            )

        if report.report_status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Report is already {report.report_status}",
            )

        # Update report status
        report.report_status = "passed"
        report.reviewed_by = admin_id
        report.reviewed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(report)

        return report


class CommentService:
    def __init__(self, db: Session):
        self.db = db

    def create_comment(self, post_id: int, comment_in, user_id: int) -> Comment:
        """Create a new comment on a post"""
        # Check if post exists
        post = self.db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )

        # Check if user is a member of the community
        membership = (
            self.db.query(CommunityMember)
            .filter(
                and_(
                    CommunityMember.community_id == post.community_id,
                    CommunityMember.user_id == user_id,
                )
            )
            .first()
        )

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Must be a member to comment on posts",
            )

        # If replying to a comment, verify parent exists
        if comment_in.parent_comment_id:
            parent = (
                self.db.query(Comment)
                .filter(Comment.id == comment_in.parent_comment_id)
                .first()
            )
            if not parent or parent.post_id != post_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent comment not found",
                )

        # Create comment
        comment = Comment(
            post_id=post_id,
            user_id=user_id,
            content=comment_in.content,
            parent_comment_id=comment_in.parent_comment_id,
        )

        self.db.add(comment)

        # Update post comments count
        post.comments_count += 1

        self.db.commit()
        self.db.refresh(comment)

        return comment

    def get_comments(
        self,
        post_id: int,
        page: int = 1,
        size: int = 20,
        user_id: Optional[int] = None,
    ) -> Tuple[List[Comment], dict]:
        """Get comments for a post with pagination (top-level comments only)"""
        # Get top-level comments (no parent)
        query = (
            self.db.query(Comment)
            .filter(
                and_(
                    Comment.post_id == post_id,
                    Comment.is_deleted == False,
                    Comment.parent_comment_id == None,
                )
            )
            .options(
                selectinload(Comment.author),
                selectinload(Comment.replies).selectinload(Comment.author),
            )
        )

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * size
        comments = (
            query.order_by(Comment.created_at.asc()).offset(offset).limit(size).all()
        )

        # Pagination metadata
        total_pages = math.ceil(total / size)
        pagination = {
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
        }

        return comments, pagination

    def update_comment(
        self, comment_id: int, comment_in, user_id: int
    ) -> Optional[Comment]:
        """Update a comment"""
        comment = self.db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            return None

        # Check if user is the author
        if comment.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the comment author can edit this comment",
            )

        if comment.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot edit a deleted comment",
            )

        # Update content
        comment.content = comment_in.content
        comment.is_edited = True
        comment.edited_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(comment)

        return comment

    def delete_comment(self, comment_id: int, user_id: int) -> bool:
        """Delete a comment (soft delete)"""
        comment = (
            self.db.query(Comment)
            .filter(Comment.id == comment_id)
            .options(selectinload(Comment.post))
            .first()
        )

        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found",
            )

        # Check if user is the author or a moderator/admin
        is_author = comment.user_id == user_id

        if comment.post:
            membership = (
                self.db.query(CommunityMember)
                .filter(
                    and_(
                        CommunityMember.community_id == comment.post.community_id,
                        CommunityMember.user_id == user_id,
                        CommunityMember.role.in_(["owner", "admin", "moderator"]),
                    )
                )
                .first()
            )
        else:
            membership = None

        if not is_author and not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the comment author or moderators can delete this comment",
            )

        # Soft delete
        comment.is_deleted = True
        comment.content = "[Comment deleted]"

        # Update post comments count
        if comment.post:
            comment.post.comments_count = max(0, comment.post.comments_count - 1)

        self.db.commit()

        return True
