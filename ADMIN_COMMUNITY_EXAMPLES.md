# Example: Protecting Community Endpoints with Admin Access

This file shows examples of how to add admin-only endpoints to the community system.

## Example 1: Admin View All Communities (Including Private)

```python
# Add to app/routers/community.py

from app.core.dependencies import get_current_admin
from app.models.admin import Admin

@router.get("/admin/all", response_model=CommunityListResponse)
def admin_list_all_communities(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Admin endpoint: List all communities including private ones.
    Regular users cannot see this endpoint.
    """
    service = CommunityService(db)
    communities = db.query(Community).offset(skip).limit(limit).all()
    total = db.query(Community).count()

    return CommunityListResponse(
        communities=communities,
        total=total,
        skip=skip,
        limit=limit
    )
```

## Example 2: Admin Delete Community

```python
# Requires senior admin (level 500+)
from app.core.dependencies import require_admin_level

@router.delete("/{community_id}/admin", status_code=204)
def admin_delete_community(
    community_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin_level(500)),
):
    """
    Admin endpoint: Delete a community permanently.
    Requires admin level 500 or higher.
    """
    community = db.query(Community).filter(Community.id == community_id).first()
    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community not found"
        )

    db.delete(community)
    db.commit()

    # Log the action
    logger.info(
        f"Community {community_id} deleted by admin {current_admin.username} "
        f"(level {current_admin.level})"
    )

    return None
```

## Example 3: Admin Pin/Unpin Posts

```python
@router.patch("/{community_id}/posts/{post_id}/pin")
def admin_toggle_pin(
    community_id: int,
    post_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin_level(50)),
):
    """
    Admin endpoint: Toggle pin status of a post.
    Requires moderator level (50+).
    """
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.community_id == community_id
    ).first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    post.is_pinned = not post.is_pinned
    db.commit()
    db.refresh(post)

    return {
        "post_id": post.id,
        "is_pinned": post.is_pinned,
        "pinned_by": current_admin.username
    }
```

## Example 4: Admin Moderate Content (Delete Posts)

```python
@router.delete("/{community_id}/posts/{post_id}/admin")
def admin_delete_post(
    community_id: int,
    post_id: int,
    reason: str = Query(..., description="Reason for deletion"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin_level(50)),
):
    """
    Admin endpoint: Delete a post (moderation).
    Requires moderator level (50+).
    """
    post = db.query(Post).filter(
        Post.id == post_id,
        Post.community_id == community_id
    ).first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # Soft delete
    post.is_deleted = True
    db.commit()

    # Log moderation action
    logger.warning(
        f"Post {post_id} deleted by moderator {current_admin.username}. "
        f"Reason: {reason}"
    )

    return {
        "message": "Post deleted by moderator",
        "post_id": post_id,
        "deleted_by": current_admin.username,
        "reason": reason
    }
```

## Example 5: Admin View Statistics

```python
@router.get("/admin/statistics")
def get_community_statistics(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    """
    Admin endpoint: Get comprehensive community statistics.
    """
    from sqlalchemy import func

    total_communities = db.query(func.count(Community.id)).scalar()
    public_communities = db.query(func.count(Community.id)).filter(
        Community.is_public == True
    ).scalar()
    private_communities = total_communities - public_communities

    total_members = db.query(func.count(CommunityMember.id)).scalar()
    total_posts = db.query(func.count(Post.id)).filter(
        Post.is_deleted == False
    ).scalar()
    total_reactions = db.query(func.count(PostReaction.id)).scalar()

    # Most active communities
    active_communities = db.query(
        Community.id,
        Community.name,
        func.count(Post.id).label('post_count')
    ).join(Post).group_by(Community.id).order_by(
        func.count(Post.id).desc()
    ).limit(10).all()

    return {
        "overview": {
            "total_communities": total_communities,
            "public_communities": public_communities,
            "private_communities": private_communities,
            "total_members": total_members,
            "total_posts": total_posts,
            "total_reactions": total_reactions
        },
        "most_active_communities": [
            {
                "id": c.id,
                "name": c.name,
                "post_count": c.post_count
            }
            for c in active_communities
        ],
        "admin": {
            "name": current_admin.name,
            "level": current_admin.level
        }
    }
```

## Example 6: Admin Manage Member Roles

```python
@router.patch("/{community_id}/members/{user_id}/role")
def admin_update_member_role(
    community_id: int,
    user_id: int,
    role_update: UpdateMemberRoleRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin_level(100)),
):
    """
    Admin endpoint: Update a member's role in a community.
    Requires manager level (100+).
    """
    member = db.query(CommunityMember).filter(
        CommunityMember.community_id == community_id,
        CommunityMember.user_id == user_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this community"
        )

    # Prevent changing owner role
    if member.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify owner role"
        )

    member.role = role_update.role
    db.commit()
    db.refresh(member)

    logger.info(
        f"Member {user_id} role changed to {role_update.role} in community "
        f"{community_id} by admin {current_admin.username}"
    )

    return {
        "community_id": community_id,
        "user_id": user_id,
        "new_role": member.role,
        "updated_by": current_admin.username
    }
```

## Example 7: Admin Ban User from Community

```python
@router.post("/{community_id}/members/{user_id}/ban")
def admin_ban_user_from_community(
    community_id: int,
    user_id: int,
    reason: str = Query(..., description="Reason for ban"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin_level(50)),
):
    """
    Admin endpoint: Ban a user from a community.
    Requires moderator level (50+).
    """
    # Check if member exists
    member = db.query(CommunityMember).filter(
        CommunityMember.community_id == community_id,
        CommunityMember.user_id == user_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this community"
        )

    # Cannot ban owner
    if member.role == "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot ban community owner"
        )

    # Remove member
    db.delete(member)

    # Update community member count
    community = db.query(Community).filter(Community.id == community_id).first()
    if community:
        community.members_count -= 1

    db.commit()

    # You could also add to a banned_users table here

    logger.warning(
        f"User {user_id} banned from community {community_id} by "
        f"moderator {current_admin.username}. Reason: {reason}"
    )

    return {
        "message": "User banned from community",
        "community_id": community_id,
        "user_id": user_id,
        "banned_by": current_admin.username,
        "reason": reason
    }
```

## Example 8: Optional Admin Access (Enhanced Stats)

```python
from typing import Union
from app.core.dependencies import get_optional_admin

@router.get("/{community_id}/statistics")
def get_community_stats(
    community_id: int,
    db: Session = Depends(get_db),
    current_admin: Union[Admin, bool] = Depends(get_optional_admin),
):
    """
    Get community statistics.
    Admins see more detailed stats than regular users.
    """
    community = db.query(Community).filter(Community.id == community_id).first()
    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community not found"
        )

    # Basic stats for everyone
    stats = {
        "community_id": community_id,
        "name": community.name,
        "members_count": community.members_count,
        "posts_count": community.posts_count
    }

    # Enhanced stats for admins
    if isinstance(current_admin, Admin):
        from sqlalchemy import func

        # Recent activity
        posts_last_week = db.query(func.count(Post.id)).filter(
            Post.community_id == community_id,
            Post.created_at >= func.now() - timedelta(days=7)
        ).scalar()

        # Top contributors
        top_contributors = db.query(
            User.id,
            User.full_name,
            func.count(Post.id).label('post_count')
        ).join(Post).filter(
            Post.community_id == community_id
        ).group_by(User.id).order_by(
            func.count(Post.id).desc()
        ).limit(5).all()

        stats["admin_stats"] = {
            "posts_last_week": posts_last_week,
            "top_contributors": [
                {
                    "user_id": u.id,
                    "name": u.full_name,
                    "post_count": u.post_count
                }
                for u in top_contributors
            ],
            "is_public": community.is_public,
            "invite_code": community.invite_code if not community.is_public else None,
            "viewed_by_admin": current_admin.username
        }

    return stats
```

## Complete Router Structure

Here's how your community router would look with admin endpoints:

```python
# app/routers/community.py

router = APIRouter(
    prefix="/communities",
    tags=["Communities"],
)

# ==================== Public/User Endpoints ====================
@router.post("/")                              # Create community
@router.get("/")                               # List public communities
@router.get("/{id}")                           # Get community details
@router.patch("/{id}")                         # Update community (owner)
@router.post("/{id}/join")                     # Join community
@router.post("/{id}/leave")                    # Leave community
@router.post("/{id}/posts")                    # Create post
@router.get("/{id}/posts")                     # List posts

# ==================== Admin-Only Endpoints ====================
@router.get("/admin/all")                      # View all communities
@router.get("/admin/statistics")               # System-wide stats
@router.delete("/{id}/admin")                  # Delete community (level 500+)
@router.patch("/{id}/posts/{post_id}/pin")     # Pin post (level 50+)
@router.delete("/{id}/posts/{post_id}/admin")  # Delete post (level 50+)
@router.patch("/{id}/members/{user_id}/role")  # Change member role (level 100+)
@router.post("/{id}/members/{user_id}/ban")    # Ban user (level 50+)

# ==================== Optional Admin Access ====================
@router.get("/{id}/statistics")                # Enhanced stats for admins
```

## Admin Level Recommendations for Community System

| Level | Role         | Community Permissions                    |
| ----- | ------------ | ---------------------------------------- |
| 50+   | Moderator    | Pin posts, delete posts, ban users       |
| 100+  | Manager      | Change member roles, view detailed stats |
| 500+  | Senior Admin | Delete communities, full moderation      |
| 999   | Super Admin  | All permissions, system configuration    |

## Testing Admin Community Endpoints

```bash
# 1. Login as admin
TOKEN=$(curl -s -X POST http://localhost:8000/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username_or_email":"admin","password":"Admin@123"}' \
  | jq -r '.access_token')

# 2. View all communities (admin only)
curl -X GET http://localhost:8000/communities/admin/all \
  -H "Authorization: Bearer $TOKEN"

# 3. Get statistics
curl -X GET http://localhost:8000/communities/admin/statistics \
  -H "Authorization: Bearer $TOKEN"

# 4. Delete a post (moderator)
curl -X DELETE http://localhost:8000/communities/1/posts/5/admin?reason=spam \
  -H "Authorization: Bearer $TOKEN"
```
