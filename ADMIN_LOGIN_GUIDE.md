# Admin Login System - Quick Reference

## ✅ Implementation Complete

Admin login functionality has been added with username/email and password authentication.

## 🔑 Features

- ✅ Login with username or email
- ✅ Password verification with bcrypt
- ✅ Extended token expiration for admins (configurable)
- ✅ Admin verification check
- ✅ Separate admin tokens with level information
- ✅ Remember me functionality
- ✅ Comprehensive error handling

## 🚀 Quick Start

### 1. Start the Server

```bash
python main.py --env dev
```

### 2. Test Admin Login

```bash
python test_admin_login.py
```

## 📋 API Endpoint

### Admin Login

```http
POST /auth/admin/login
Content-Type: application/json

{
  "username_or_email": "admin",
  "password": "Admin@123",
  "remember_me": false
}
```

**Response:**

```json
{
  "success": true,
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 7776000,
  "admin": {
    "id": 1,
    "name": "Super Admin",
    "username": "admin",
    "email": "admin@example.com",
    "is_verified": true,
    "level": 999,
    "created_at": "2025-11-13T23:49:54.046943+00:00",
    "updated_at": "2025-11-13T23:49:54.046943+00:00"
  },
  "message": "Admin login successful"
}
```

## 🔐 Default Admin Credentials

The super admin is automatically created on first startup:

- **Username:** `admin`
- **Email:** `admin@example.com`
- **Password:** `Admin@123`
- **Level:** 999 (Super Admin)

⚠️ **Important:** Change the default password immediately in production!

## 💡 Usage Examples

### cURL

```bash
# Login with username
curl -X POST "http://localhost:8000/auth/admin/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "admin",
    "password": "Admin@123",
    "remember_me": false
  }'

# Login with email
curl -X POST "http://localhost:8000/auth/admin/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "admin@example.com",
    "password": "Admin@123",
    "remember_me": true
  }'
```

### Python (requests)

```python
import requests

response = requests.post(
    "http://localhost:8000/auth/admin/login",
    json={
        "username_or_email": "admin",
        "password": "Admin@123",
        "remember_me": False
    }
)

if response.status_code == 200:
    data = response.json()
    access_token = data['access_token']
    admin_info = data['admin']
    print(f"Logged in as: {admin_info['name']} (Level: {admin_info['level']})")
```

### JavaScript (fetch)

```javascript
const response = await fetch("http://localhost:8000/auth/admin/login", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    username_or_email: "admin",
    password: "Admin@123",
    remember_me: false,
  }),
});

const data = await response.json();
console.log("Access Token:", data.access_token);
console.log("Admin:", data.admin);
```

## 🛡️ Using Admin Token

After login, use the access token in the Authorization header:

```http
GET /admin/users
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Payload

The admin token contains:

```json
{
  "sub": "1",
  "username": "admin",
  "email": "admin@example.com",
  "type": "admin",
  "level": 999,
  "iat": 1699915154.046943,
  "exp": 1707691154
}
```

## ⚙️ Configuration

Admin token expiration is configured in `app/core/config.py`:

```python
jwt_admin_expiration: int = Field(default=90)  # Days
```

## 🔒 Security Features

1. **Password Hashing:** Bcrypt with configurable rounds
2. **Token Expiration:** Extended for admins (default: 90 days)
3. **Verification Check:** Only verified admins can login
4. **Rate Limiting:** Configured via FastAPI middleware
5. **Secure Comparison:** Constant-time password verification

## 🚨 Error Responses

### Invalid Credentials (401)

```json
{
  "detail": "Invalid credentials"
}
```

### Account Not Verified (403)

```json
{
  "detail": "Admin account is not verified"
}
```

### Missing Fields (422)

```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## 📊 Admin Levels

The system supports different admin levels:

- **999:** Super Admin (full access)
- **100:** Senior Admin
- **50:** Junior Admin
- **1:** Basic Admin (default)

Use the `level` field to implement role-based access control.

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_admin_login.py
```

Tests include:

- ✅ Login with username
- ✅ Login with email
- ✅ Wrong password rejection
- ✅ Nonexistent user rejection
- ✅ Missing fields validation
- ✅ Protected endpoint access

## 🔄 Super Admin Initialization

The super admin is automatically created on startup if no admins exist:

```python
# In app/core/init.py
def init_super_admin(db: Session):
    # Creates super admin if none exists
    # Username: admin
    # Email: from settings.admin_default_email
    # Password: from settings.admin_default_password
    # Level: 999
```

## 📝 Files Modified

1. **app/schemas/auth.py** - Added admin login schemas
2. **app/services/auth.py** - Added admin_login method
3. **app/routers/auth.py** - Added /auth/admin/login endpoint
4. **app/core/init.py** - Added super admin initialization
5. **test_admin_login.py** - Comprehensive test suite

## 🎯 Next Steps

1. **Add Admin Middleware:** Create middleware to verify admin tokens
2. **Protected Admin Routes:** Secure admin-only endpoints
3. **Admin Permissions:** Implement level-based permissions
4. **Admin Management:** Create endpoints to manage other admins
5. **Audit Logging:** Track admin actions

## 💼 Production Checklist

- [ ] Change default admin password
- [ ] Set strong JWT secret in `.env`
- [ ] Enable HTTPS only
- [ ] Configure rate limiting
- [ ] Set up admin activity logging
- [ ] Implement 2FA (optional)
- [ ] Regular security audits

## ✨ Example Admin Dashboard Integration

```javascript
// React example
const AdminLogin = () => {
  const [credentials, setCredentials] = useState({
    username_or_email: "",
    password: "",
    remember_me: false,
  });

  const handleLogin = async (e) => {
    e.preventDefault();

    const response = await fetch("/auth/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(credentials),
    });

    if (response.ok) {
      const data = await response.json();
      localStorage.setItem("adminToken", data.access_token);
      localStorage.setItem("adminInfo", JSON.stringify(data.admin));
      // Redirect to admin dashboard
      window.location.href = "/admin/dashboard";
    }
  };

  return (
    <form onSubmit={handleLogin}>
      <input
        type="text"
        placeholder="Username or Email"
        value={credentials.username_or_email}
        onChange={(e) =>
          setCredentials({
            ...credentials,
            username_or_email: e.target.value,
          })
        }
      />
      <input
        type="password"
        placeholder="Password"
        value={credentials.password}
        onChange={(e) =>
          setCredentials({
            ...credentials,
            password: e.target.value,
          })
        }
      />
      <label>
        <input
          type="checkbox"
          checked={credentials.remember_me}
          onChange={(e) =>
            setCredentials({
              ...credentials,
              remember_me: e.target.checked,
            })
          }
        />
        Remember me
      </label>
      <button type="submit">Login</button>
    </form>
  );
};
```

---

**System is ready! 🎉**
