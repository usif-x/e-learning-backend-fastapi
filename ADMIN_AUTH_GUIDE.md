# Admin Authentication & Authorization Guide

## Overview

Complete admin authentication system with JWT tokens and role-based access control (RBAC) using admin levels.

## Admin Model

### Admin Levels

- **Level 1-99**: Regular admins (basic permissions)
- **Level 100-499**: Mid-level admins (moderate permissions)
- **Level 500-998**: Senior admins (elevated permissions)
- **Level 999**: Super admin (full permissions, can create other admins)

### Admin Fields

```python
{
    "id": int,
    "name": str,
    "username": str (unique),
    "email": str (unique),
    "password": str (hashed),
    "is_verified": bool,
    "level": int (1-999),
    "created_at": datetime,
    "updated_at": datetime
}
```

## Authentication Flow

### 1. Admin Login

```http
POST /auth/admin/login

Request:
{
    "username_or_email": "admin",  # Can be username or email
    "password": "Admin@123"
}

Response (200 OK):
{
    "success": true,
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 7776000,  # 90 days
    "admin": {
        "id": 1,
        "name": "Super Admin",
        "username": "admin",
        "email": "admin@example.com",
        "level": 999,
        "is_verified": true,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
    },
    "message": "Admin login successful"
}
```

### 2. Token Format

#### Access Token Payload

```json
{
  "sub": "1",
  "admin_id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "type": "admin",
  "level": 999,
  "iat": 1234567890,
  "exp": 1234567890,
  "iss": "your-app-name"
}
```

#### Refresh Token Payload

```json
{
  "sub": "1",
  "admin_id": 1,
  "username": "admin",
  "type": "admin_refresh",
  "iat": 1234567890,
  "exp": 1234567890,
  "iss": "your-app-name"
}
```

## Using Admin Authentication

### Protect Endpoints with Admin Auth

#### 1. Require Any Admin

```python
from fastapi import Depends
from app.core.dependencies import get_current_admin
from app.models.admin import Admin

@router.get("/admin/dashboard")
async def admin_dashboard(
    current_admin: Admin = Depends(get_current_admin)
):
    return {"message": f"Welcome, {current_admin.name}"}
```

#### 2. Require Specific Admin Level

```python
from app.core.dependencies import require_admin_level

@router.post("/admin/create")
async def create_admin(
    admin_data: CreateAdmin,
    current_admin: Admin = Depends(require_admin_level(999))
):
    # Only super admins (level 999) can access
    return {"message": "Admin created"}

@router.delete("/courses/{id}")
async def delete_course(
    id: int,
    current_admin: Admin = Depends(require_admin_level(500))
):
    # Admins level 500+ can delete courses
    return {"message": "Course deleted"}
```

#### 3. Optional Admin Authentication

```python
from typing import Union
from app.core.dependencies import get_optional_admin

@router.get("/stats")
async def get_stats(
    current_admin: Union[Admin, bool] = Depends(get_optional_admin)
):
    if isinstance(current_admin, Admin):
        # Admin is authenticated, show detailed stats
        return {"detailed_stats": "..."}
    else:
        # No admin auth, show public stats
        return {"public_stats": "..."}
```

## API Endpoints

### Get Current Admin Profile

```http
GET /admin/me
Authorization: Bearer <admin_token>

Response (200 OK):
{
    "id": 1,
    "name": "Super Admin",
    "username": "admin",
    "email": "admin@example.com",
    "level": 999,
    "is_verified": true,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
}
```

### Create New Admin (Super Admin Only)

```http
POST /admin/create
Authorization: Bearer <super_admin_token>

Request:
{
    "name": "New Admin",
    "username": "newadmin",
    "email": "newadmin@example.com",
    "password": "SecurePassword@123",
    "level": 50,
    "is_verified": true
}

Response (201 Created):
{
    "message": "Admin created successfully",
    "admin": {
        "id": 2,
        "name": "New Admin",
        "username": "newadmin",
        "email": "newadmin@example.com",
        "level": 50,
        "is_verified": true,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
    }
}
```

## Frontend Integration

### JavaScript/TypeScript Example

```javascript
// Admin Login
async function adminLogin(usernameOrEmail, password) {
  const response = await fetch("http://localhost:8000/auth/admin/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      username_or_email: usernameOrEmail,
      password: password,
    }),
  });

  if (response.ok) {
    const data = await response.json();
    // Store tokens
    localStorage.setItem("admin_access_token", data.access_token);
    localStorage.setItem("admin_refresh_token", data.refresh_token);
    localStorage.setItem("admin_data", JSON.stringify(data.admin));
    return data;
  }

  throw new Error("Login failed");
}

// Get Current Admin Profile
async function getCurrentAdmin() {
  const token = localStorage.getItem("admin_access_token");

  const response = await fetch("http://localhost:8000/admin/me", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (response.ok) {
    return await response.json();
  }

  throw new Error("Failed to get admin profile");
}

// Protected Request Example
async function makeAdminRequest(endpoint, options = {}) {
  const token = localStorage.getItem("admin_access_token");

  const response = await fetch(`http://localhost:8000${endpoint}`, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (response.status === 401) {
    // Token expired, redirect to login
    window.location.href = "/admin/login";
    return;
  }

  return await response.json();
}
```

### React Example

```jsx
import { useState, useEffect } from "react";

function AdminDashboard() {
  const [admin, setAdmin] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAdmin() {
      try {
        const token = localStorage.getItem("admin_access_token");
        const response = await fetch("http://localhost:8000/admin/me", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          setAdmin(data);
        } else {
          // Redirect to login
          window.location.href = "/admin/login";
        }
      } catch (error) {
        console.error("Failed to load admin:", error);
      } finally {
        setLoading(false);
      }
    }

    loadAdmin();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (!admin) return <div>Not authenticated</div>;

  return (
    <div>
      <h1>Welcome, {admin.name}</h1>
      <p>Username: {admin.username}</p>
      <p>Level: {admin.level}</p>
      <p>Email: {admin.email}</p>
    </div>
  );
}
```

## Security Best Practices

### 1. Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character

### 2. Token Storage

- **Frontend**: Store tokens in localStorage or httpOnly cookies
- **Never expose tokens**: Don't log tokens or send them in URLs
- **Refresh tokens**: Implement token refresh logic before expiration

### 3. HTTPS Only

- Always use HTTPS in production
- Tokens should never be sent over HTTP

### 4. Rate Limiting

Add rate limiting to login endpoint:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/auth/admin/login")
@limiter.limit("5/minute")  # 5 attempts per minute
async def admin_login(request: Request, ...):
    ...
```

## Testing

### Run Test Suite

```bash
# Start the server
python main.py

# In another terminal, run tests
python test_admin_auth.py
```

### Test Cases

1. ✅ Admin Login with valid credentials
2. ✅ Get current admin profile
3. ✅ Block unauthorized access
4. ✅ Block invalid tokens
5. ✅ Block create admin without auth
6. ✅ Allow create admin with super admin auth

### Manual Testing with cURL

```bash
# Login
curl -X POST http://localhost:8000/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "admin",
    "password": "Admin@123"
  }'

# Get Current Admin (replace TOKEN)
curl -X GET http://localhost:8000/admin/me \
  -H "Authorization: Bearer TOKEN"

# Create Admin (replace TOKEN)
curl -X POST http://localhost:8000/admin/create \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Admin",
    "username": "testadmin",
    "email": "test@admin.com",
    "password": "Test@123",
    "level": 50,
    "is_verified": true
  }'
```

## Error Handling

### Common Errors

#### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

**Solution**: Provide valid Bearer token

#### 403 Forbidden

```json
{
  "detail": "Admin level 999 or higher required"
}
```

**Solution**: Need higher admin level

#### 401 Invalid Token

```json
{
  "detail": "Invalid token: Signature has expired"
}
```

**Solution**: Refresh token or login again

## Admin Level Recommendations

### Level 1-49: Basic Admin

- View statistics
- View users
- View courses
- Moderate comments

### Level 50-99: Moderator

- Basic permissions +
- Edit courses
- Edit users
- Ban users
- Delete comments/posts

### Level 100-499: Manager

- Moderator permissions +
- Create courses
- Manage categories
- Manage communities
- View financial reports

### Level 500-998: Senior Admin

- Manager permissions +
- Delete courses
- Delete users
- System configuration
- Full financial access

### Level 999: Super Admin

- All permissions
- Create/delete admins
- System administration
- Database access

## Troubleshooting

### Issue: "Not authenticated"

- Ensure Authorization header is present
- Check token format: `Bearer <token>`
- Verify token hasn't expired

### Issue: "Admin not found"

- Token is valid but admin was deleted
- Admin ID in token doesn't exist in database

### Issue: "Admin account is not verified"

- Admin exists but `is_verified` is false
- Super admin needs to verify the account

### Issue: "Admin level X required"

- Current admin level is too low
- Request super admin to upgrade level

## Default Super Admin

**Credentials**:

- Username: `admin`
- Email: `admin@example.com`
- Password: `Admin@123`
- Level: `999`

**⚠️ IMPORTANT**: Change these credentials in production!

## Next Steps

1. **Change Default Password**: Update super admin password after first login
2. **Create Admin Levels**: Define specific levels for your organization
3. **Add Audit Logging**: Track admin actions for security
4. **Implement 2FA**: Add two-factor authentication for admins
5. **Session Management**: Add ability to view/revoke active sessions
