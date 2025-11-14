# Community System Documentation

## Overview

Complete community system with groups, members, posts (text/image/audio), reactions, and comments.

## Database Schema

### Tables Created

1. **communities** - Community groups (public/private)
2. **community_members** - Membership tracking with roles
3. **posts** - User posts within communities
4. **post_media** - Media attachments (images/audio)
5. **post_reactions** - Reactions/likes on posts
6. **comments** - Comments with nested replies

### Key Features

- Public and private communities with invite codes
- Role-based access control (owner/admin/moderator/member)
- Posts with text, images, and audio
- Reaction system (like/love/laugh/sad/angry)
- Nested comments with replies
- Soft delete for posts and comments
- Statistics tracking (member count, post count, reaction count)

## Setup Instructions

### 1. Run Database Migration

```bash
# Generate migration
alembic revision --autogenerate -m "Add community system"

# Apply migration
alembic upgrade head
```

### 2. Verify Tables Created

```bash
# Connect to PostgreSQL
psql -U your_username -d your_database

# List tables
\dt

# Check community table structure
\d communities
```

## API Endpoints

### Communities

#### Create Community

```http
POST /api/communities
Authorization: Bearer <token>

{
  "name": "Python Developers",
  "description": "Community for Python enthusiasts",
  "is_public": true,
  "allow_member_posts": true,
  "require_approval": false
}

Response:
{
  "id": 1,
  "name": "Python Developers",
  "description": "Community for Python enthusiasts",
  "image": null,
  "is_public": true,
  "invite_code": "ABC123",
  "allow_member_posts": true,
  "require_approval": false,
  "members_count": 1,
  "posts_count": 0,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

#### List Communities

```http
GET /api/communities?skip=0&limit=20
Authorization: Bearer <token> (optional)

Response:
[
  {
    "id": 1,
    "name": "Python Developers",
    "description": "Community for Python enthusiasts",
    "image": null,
    "is_public": true,
    "members_count": 150,
    "posts_count": 45,
    "created_at": "2024-01-01T00:00:00"
  }
]
```

#### Get Community Details

```http
GET /api/communities/1
Authorization: Bearer <token> (optional)

Response:
{
  "id": 1,
  "name": "Python Developers",
  "description": "Community for Python enthusiasts",
  "image": null,
  "is_public": true,
  "invite_code": "ABC123",
  "allow_member_posts": true,
  "require_approval": false,
  "members_count": 150,
  "posts_count": 45,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

#### Update Community

```http
PATCH /api/communities/1
Authorization: Bearer <token>

{
  "description": "Updated description",
  "is_public": false
}

Response: Updated community object
```

#### Join Community

```http
# Option 1: Invite code as query parameter (recommended)
POST /api/communities/1/join?invite_code=ABC123
Authorization: Bearer <token>

# Option 2: Invite code in request body
POST /api/communities/1/join
Authorization: Bearer <token>
{
  "invite_code": "ABC123"
}

# For public communities, no invite code needed
POST /api/communities/1/join
Authorization: Bearer <token>

Response:
{
  "id": 1,
  "community_id": 1,
  "user_id": 5,
  "role": "member",
  "joined_via": "invite_link",  // or "direct" for public
  "joined_at": "2024-01-01T00:00:00"
}
```

#### Leave Community

```http
POST /api/communities/1/leave
Authorization: Bearer <token>

Response: {"message": "Successfully left the community"}
```

#### Upload Community Image

```http
POST /api/communities/1/upload-image
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <image_file>

Response:
{
  "id": 1,
  "name": "Python Developers",
  "image": "http://localhost:8000/storage/communities/uuid-filename.jpg",
  ...
}
```

#### Regenerate Invite Code

```http
POST /api/communities/1/regenerate-invite
Authorization: Bearer <token>

Response:
{
  "id": 1,
  "name": "Private Community",
  "description": "...",
  "is_public": false,
  "invite_code": "NEW_CODE_HERE",  # New unique invite code
  "allow_member_posts": true,
  "require_approval": false,
  "members_count": 5,
  "posts_count": 10,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}

Note: Only owners and admins can regenerate invite codes.
This invalidates the previous invite code.
```

### Posts

#### Create Post

```http
POST /api/communities/1/posts
Authorization: Bearer <token>

{
  "content": "Check out this awesome Python library!",
  "is_pinned": false
}

Response:
{
  "id": 1,
  "community_id": 1,
  "user_id": 5,
  "content": "Check out this awesome Python library!",
  "is_pinned": false,
  "is_edited": false,
  "is_deleted": false,
  "reactions_count": 0,
  "comments_count": 0,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

#### List Posts

```http
GET /api/communities/1/posts?page=1&size=20
Authorization: Bearer <token> (optional)

Response: List of posts (pinned posts first, then by created_at DESC)
{
  "posts": [...],
  "total": 45,
  "page": 1,
  "size": 20,
  "total_pages": 3
}
```

#### Get Specific Post

```http
GET /api/communities/1/posts/5
Authorization: Bearer <token> (optional)

Response:
{
  "id": 5,
  "community_id": 1,
  "user_id": 5,
  "content": "This is a specific post",
  "is_pinned": false,
  "is_edited": false,
  "is_deleted": false,
  "reactions_count": 10,
  "comments_count": 3,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00",
  "author": {
    "id": 5,
    "full_name": "John Doe",
    "profile_picture": "...",
    "telegram_username": "johndoe"
  },
  "media": [
    {
      "id": 1,
      "media_type": "image",
      "media_url": "storage/posts/uuid.jpg"
    }
  ],
  "user_reaction": "like"  // null if not reacted
}
```

#### Update Post

```http
PATCH /api/posts/1
Authorization: Bearer <token>

{
  "content": "Updated content",
  "is_pinned": true
}

Response: Updated post object
```

#### Delete Post

```http
DELETE /api/posts/1
Authorization: Bearer <token>

Response: {"message": "Post deleted successfully"}
```

#### Add Post Media

```http
POST /api/posts/1/media?media_type=image
Authorization: Bearer <token>
Content-Type: multipart/form-data

media_file: <image_file>

# Supported image types: .jpg, .jpeg, .png, .gif, .webp, .svg
# Max size: 5MB

Response:
{
  "id": 1,
  "post_id": 1,
  "media_type": "image",
  "media_url": "http://localhost:8000/storage/posts/uuid-file.jpg",
  "file_size": 154623,
  "duration": null,
  "position": 0
}
```

```http
POST /api/posts/1/media?media_type=audio
Authorization: Bearer <token>
Content-Type: multipart/form-data

media_file: <audio_file>

# Supported audio types: .mp3, .wav, .ogg, .m4a, .aac, .flac
# Max size: 20MB

Response:
{
  "id": 2,
  "post_id": 1,
  "media_type": "audio",
  "media_url": "http://localhost:8000/storage/posts/uuid-audio.mp3",
  "file_size": 2458921,
  "duration": null,
  "position": 1
}
```

#### Add Reaction

```http
POST /api/posts/1/reactions
Authorization: Bearer <token>

{
  "reaction_type": "like"
}

Response:
{
  "id": 1,
  "post_id": 1,
  "user_id": 5,
  "reaction_type": "like",
  "created_at": "2024-01-01T00:00:00"
}

Note: Calling again with the same reaction removes it (toggle)
```

#### Remove Reaction

```http
DELETE /api/posts/1/reactions
Authorization: Bearer <token>

Response: {"message": "Reaction removed successfully"}
```

### Comments

#### Create Comment

```http
POST /api/communities/posts/1/comments
Authorization: Bearer <token>

{
  "content": "Great post! Thanks for sharing.",
  "parent_comment_id": null  # null for top-level, or ID to reply
}

Response:
{
  "id": 1,
  "post_id": 1,
  "user_id": 5,
  "parent_comment_id": null,
  "content": "Great post! Thanks for sharing.",
  "is_edited": false,
  "reactions_count": 0,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00",
  "edited_at": null,
  "author": {
    "id": 5,
    "full_name": "John Doe",
    "profile_picture": "...",
    "telegram_username": "johndoe"
  },
  "replies": []
}
```

#### Reply to Comment

```http
POST /api/communities/posts/1/comments
Authorization: Bearer <token>

{
  "content": "I agree with your point!",
  "parent_comment_id": 1  # ID of comment to reply to
}
```

#### List Comments

```http
GET /api/communities/posts/1/comments?page=1&size=20
Authorization: Bearer <token> (optional)

Response:
{
  "comments": [
    {
      "id": 1,
      "content": "Great post!",
      "author": {...},
      "replies": [
        {
          "id": 2,
          "content": "I agree!",
          "parent_comment_id": 1,
          "author": {...}
        }
      ]
    }
  ],
  "total": 10,
  "page": 1,
  "size": 20,
  "total_pages": 1
}
```

#### Update Comment

```http
PATCH /api/communities/comments/1
Authorization: Bearer <token>

{
  "content": "Updated comment content"
}

Response: Updated comment object with is_edited: true
```

#### Delete Comment

```http
DELETE /api/communities/comments/1
Authorization: Bearer <token>

Response: 204 No Content
Note: Soft delete - content becomes "[Comment deleted]"
```

## Invite Code System

### How It Works

Private communities use invite codes to control access. When a community is created as private (`is_public: false`), a unique invite code is automatically generated.

### Invite Code Features

1. **Automatic Generation**: Created automatically for private communities
2. **Unique**: Each code is unique across all communities (16-character URL-safe token)
3. **Required for Private Access**: Must provide valid code to join private communities
4. **Regenerable**: Owners/admins can regenerate codes to revoke old ones
5. **Not Used for Public**: Public communities don't have/need invite codes

### Use Cases

**Creating Private Community:**

```http
POST /api/communities
{
  "name": "VIP Members",
  "is_public": false,  // Makes it private
  "description": "Exclusive community"
}

Response includes:
{
  "id": 1,
  "invite_code": "a8Kj9mL3nP2qR5tW",  // Auto-generated
  ...
}
```

**Joining with Invite Code:**

```http
POST /api/communities/1/join
{
  "invite_code": "a8Kj9mL3nP2qR5tW"
}
```

**Regenerating Code (Security):**

```http
POST /api/communities/1/regenerate-invite

# Returns new code, old code is invalidated
{
  "invite_code": "NEW_CODE_XyZ123"
}
```

### When to Regenerate

- Code was shared publicly by mistake
- Want to revoke access for users with old code
- Suspected unauthorized sharing
- Regular security rotation
- Member removal (they still have the old code)

### Important Notes

⚠️ **Regenerating invalidates the old code** - Users with the old code can no longer join

✅ **Existing members are not affected** - Only new joins require the new code

🔒 **Only owners and admins can regenerate** - Regular members cannot access or change codes

## Role-Based Permissions

### Owner

- Full control over community
- Can update community settings
- Can delete community
- Can promote/demote members
- Can pin posts
- Can delete any posts

### Admin

- Can update community settings
- Can promote members to moderator
- Can pin posts
- Can delete any posts
- Cannot delete community

### Moderator

- Can pin posts
- Can delete posts
- Cannot update community settings
- Cannot promote members

### Member

- Can create posts (if allowed)
- Can react to posts
- Can comment on posts
- Can reply to comments
- Can edit/delete own posts and comments

## Comment Features

### Nested Replies

- Comments can have unlimited nested replies
- Use `parent_comment_id` to create threaded discussions
- Replies are loaded with the parent comment

### Comment Moderation

- Authors can edit/delete their own comments
- Community moderators/admins can delete any comment
- Deleted comments show as "[Comment deleted]"
- Edit history tracked with `is_edited` and `edited_at`

### Comment Structure

```
Post
├── Comment 1 (top-level)
│   ├── Reply 1.1
│   │   └── Reply 1.1.1
│   └── Reply 1.2
└── Comment 2 (top-level)
    └── Reply 2.1
```

## Testing

### Test Script Example

```python
# test_community.py
import requests
import json

BASE_URL = "http://localhost:8000"
TOKEN = "your_jwt_token_here"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 1. Create Community
def test_create_community():
    response = requests.post(
        f"{BASE_URL}/api/communities",
        headers=headers,
        json={
            "name": "Test Community",
            "description": "This is a test community",
            "is_public": True,
            "allow_member_posts": True
        }
    )
    print("Create Community:", response.json())
    return response.json()["id"]

# 2. Create Post
def test_create_post(community_id):
    response = requests.post(
        f"{BASE_URL}/api/communities/{community_id}/posts",
        headers=headers,
        json={
            "content": "Hello from my first post!"
        }
    )
    print("Create Post:", response.json())
    return response.json()["id"]

# 3. Add Reaction
def test_add_reaction(post_id):
    response = requests.post(
        f"{BASE_URL}/api/posts/{post_id}/reactions",
        headers=headers,
        json={
            "reaction_type": "like"
        }
    )
    print("Add Reaction:", response.json())

# 4. Create Comment
def test_create_comment(post_id):
    response = requests.post(
        f"{BASE_URL}/api/communities/posts/{post_id}/comments",
        headers=headers,
        json={
            "content": "This is a great post!",
            "parent_comment_id": None
        }
    )
    print("Create Comment:", response.json())
    return response.json()["id"]

# 5. Reply to Comment
def test_reply_comment(post_id, parent_comment_id):
    response = requests.post(
        f"{BASE_URL}/api/communities/posts/{post_id}/comments",
        headers=headers,
        json={
            "content": "I agree with this comment!",
            "parent_comment_id": parent_comment_id
        }
    )
    print("Reply to Comment:", response.json())

# 6. List Comments
def test_list_comments(post_id):
    response = requests.get(
        f"{BASE_URL}/api/communities/posts/{post_id}/comments",
        headers=headers
    )
    print("List Comments:", response.json())

# 7. Update Comment
def test_update_comment(comment_id):
    response = requests.patch(
        f"{BASE_URL}/api/communities/comments/{comment_id}",
        headers=headers,
        json={
            "content": "Updated comment content"
        }
    )
    print("Update Comment:", response.json())

# 8. List Communities
def test_list_communities():
    response = requests.get(
        f"{BASE_URL}/api/communities",
        headers=headers
    )
    print("List Communities:", response.json())

if __name__ == "__main__":
    community_id = test_create_community()
    post_id = test_create_post(community_id)
    test_add_reaction(post_id)
    comment_id = test_create_comment(post_id)
    test_reply_comment(post_id, comment_id)
    test_list_comments(post_id)
    test_update_comment(comment_id)
    test_list_communities()
```

### Run Tests

```bash
# First, make sure server is running
python main.py

# In another terminal, run test script
python test_community.py
```

## Storage Structure

```
storage/
├── communities/          # Community images
│   └── uuid-filename.jpg
├── posts/               # Post images and audio
│   ├── uuid-image.jpg
│   └── uuid-audio.mp3
├── courses/             # Course images (existing)
├── lectures/            # Lecture content (existing)
└── users/               # User avatars (existing)
```

## Reaction Types

Available reaction types:

- `like` - 👍 Like
- `love` - ❤️ Love
- `laugh` - 😂 Laugh
- `sad` - 😢 Sad
- `angry` - 😠 Angry

## Next Steps (Optional Enhancements)

### 1. Comment Endpoints

Create full CRUD endpoints for comments:

```python
# To be implemented in router
POST /api/posts/{post_id}/comments     # Create comment
GET /api/posts/{post_id}/comments      # List comments
PATCH /api/comments/{comment_id}       # Update comment
DELETE /api/comments/{comment_id}      # Delete comment
POST /api/comments/{comment_id}/reply  # Reply to comment
```

### 2. Member Management

```python
GET /api/communities/{id}/members      # List members
PATCH /api/communities/{id}/members/{user_id}  # Update role
DELETE /api/communities/{id}/members/{user_id} # Remove member
```

### 3. Search & Discovery

```python
GET /api/communities/search?q=python   # Search communities
GET /api/communities/trending          # Trending communities
GET /api/communities/recommended       # Recommended for user
```

### 4. Notifications

```python
GET /api/notifications                 # User notifications
POST /api/notifications/{id}/read      # Mark as read
```

### 5. Media Validation

Current implementation in FileUploadService:

```python
# Supported image extensions
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}

# Supported audio extensions
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"}

# File size limits
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_AUDIO_SIZE = 20 * 1024 * 1024  # 20MB
```

**Supported Media Types:**

- **Images**: JPG, JPEG, PNG, GIF, WEBP, SVG (max 5MB)
- **Audio**: MP3, WAV, OGG, M4A, AAC, FLAC (max 20MB)

## Troubleshooting

### Issue: "Community not found"

- Ensure community ID exists in database
- Check if user has access to private community
- Verify user is authenticated

### Issue: "Permission denied"

- Check user's role in community
- Verify action is allowed for that role
- Ensure user is a member of the community

### Issue: "Cannot upload media"

- Check file type is allowed (image/audio only)
- Verify file size is within limits
- Ensure storage directory has write permissions

### Issue: "Cannot join private community"

- Private communities require valid invite_code
- Check if community requires approval
- Verify invite code hasn't been regenerated

## Database Queries Examples

### Get Community with Member Count

```sql
SELECT
    c.*,
    COUNT(DISTINCT cm.id) as members_count,
    COUNT(DISTINCT p.id) as posts_count
FROM communities c
LEFT JOIN community_members cm ON c.id = cm.community_id
LEFT JOIN posts p ON c.id = p.community_id AND p.is_deleted = false
GROUP BY c.id;
```

### Get User's Communities

```sql
SELECT c.*, cm.role, cm.joined_at
FROM communities c
JOIN community_members cm ON c.id = cm.community_id
WHERE cm.user_id = :user_id
ORDER BY cm.joined_at DESC;
```

### Get Post with Reactions and Comments

```sql
SELECT
    p.*,
    COUNT(DISTINCT pr.id) as reactions_count,
    COUNT(DISTINCT c.id) as comments_count
FROM posts p
LEFT JOIN post_reactions pr ON p.id = pr.post_id
LEFT JOIN comments c ON p.id = c.post_id AND c.is_deleted = false
WHERE p.id = :post_id
GROUP BY p.id;
```

## Security Considerations

1. **Private Communities**: Ensure only members can view content
2. **Role Checks**: Validate user role before sensitive operations
3. **File Upload**: Validate file types and sizes
4. **Soft Delete**: Never permanently delete user content immediately
5. **Rate Limiting**: Add rate limits to prevent spam
6. **Invite Codes**: Regenerate codes if compromised
7. **Member Approval**: Implement approval queue for restricted communities

## Performance Tips

1. **Pagination**: Always use skip/limit parameters
2. **Eager Loading**: Use joinedload for relationships when needed
3. **Caching**: Cache community details and member counts
4. **Indexes**: Ensure indexes on foreign keys and frequently queried fields
5. **Batch Operations**: Use bulk operations for multiple inserts

## Support

For issues or questions:

1. Check error logs in `logs/` directory
2. Verify database connection and migrations
3. Test endpoints with Postman/Thunder Client
4. Review FastAPI docs at `http://localhost:8000/docs`
