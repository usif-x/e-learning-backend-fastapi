# Admin Management System

This document describes the admin management functionality in the e-learning backend system.

## Overview

The system supports a hierarchical admin structure with different permission levels:

- **Super Admin (Level 999)**: Full access to all admin management functions
- **Regular Admin (Level 1-998)**: Limited access, can only manage their own profile

## API Endpoints

### Authentication Required

All admin management endpoints require authentication with a valid admin JWT token.

### Super Admin Only Endpoints

#### Create Admin

```
POST /admin/create
Authorization: Bearer <super_admin_token>
Content-Type: application/json

{
  "name": "Admin Name",
  "username": "admin_username",
  "email": "admin@example.com",
  "password": "SecurePassword@123",
  "telegram_id": null,
  "level": 1,
  "is_verified": true
}
```

#### List All Admins

```
GET /admin/list?page=1&limit=10
Authorization: Bearer <super_admin_token>
```

#### Get Admin by ID

```
GET /admin/{admin_id}
Authorization: Bearer <super_admin_token>
```

#### Delete Admin

```
DELETE /admin/{admin_id}
Authorization: Bearer <super_admin_token>
```

#### Reset Admin Password

```
POST /admin/{admin_id}/reset-password?new_password=NewSecurePassword@123
Authorization: Bearer <super_admin_token>
```

### All Admin Endpoints

#### Get Current Admin Profile

```
GET /admin/me
Authorization: Bearer <admin_token>
```

#### Update Admin

```
PUT /admin/{admin_id}
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "name": "Updated Name",
  "email": "newemail@example.com",
  "username": "newusername",
  "password": "NewPassword@123",
  "telegram_id": "123456789",
  "level": 2,  // Only super admins can change level
  "is_verified": true  // Only super admins can change verification status
}
```

## Permission Rules

### Super Admin (Level 999)

- Can create new admins
- Can view all admins
- Can update any admin's details (including level and verification status)
- Can delete regular admins (cannot delete other super admins)
- Can reset any admin's password
- Cannot delete their own account

### Regular Admin (Level < 999)

- Can view and update their own profile
- Cannot change their own level or verification status
- Cannot access admin listing, creation, deletion, or password reset functions

## Security Features

1. **Hierarchical Permissions**: Super admins have full control, regular admins have limited access
2. **Self-Protection**: Admins cannot delete their own accounts
3. **Super Admin Protection**: Super admin accounts cannot be deleted by other super admins
4. **Password Security**: Passwords are hashed using secure hashing algorithms
5. **JWT Authentication**: All operations require valid JWT tokens

## Usage Examples

### Creating a Super Admin (Initial Setup)

```python
# This would typically be done through database migration or direct DB access
# for the initial super admin account
```

### Daily Admin Management

```python
import requests

# Login as super admin
response = requests.post('/auth/admin/login', json={
    'username_or_email': 'superadmin',
    'password': 'SuperAdmin@123'
})
token = response.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# Create a new admin
requests.post('/admin/create', json={
    'name': 'Content Manager',
    'username': 'content_admin',
    'email': 'content@example.com',
    'password': 'Content@123',
    'level': 1,
    'is_verified': True
}, headers=headers)

# List all admins
admins = requests.get('/admin/list', headers=headers).json()
print(f"Total admins: {admins['total']}")
```

## Testing

Run the admin management tests:

```bash
python test_admin_management.py
```

This will test:

- Super admin login and permissions
- Admin creation, listing, updating, and deletion
- Regular admin permission restrictions
- Password reset functionality

## Database Schema

The admin management system uses the existing `admins` table with the following key fields:

- `id`: Primary key
- `level`: Admin permission level (999 for super admin)
- `is_verified`: Account verification status
- Other standard user fields (name, username, email, password, etc.)
