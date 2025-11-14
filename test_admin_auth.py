"""
Test Admin Authentication and Authorization
"""

import json

import requests

BASE_URL = "http://localhost:8000"


def test_admin_login():
    """Test admin login"""
    print("=" * 50)
    print("Testing Admin Login...")
    print("=" * 50)

    response = requests.post(
        f"{BASE_URL}/auth/admin/login",
        json={"username_or_email": "admin", "password": "Admin@123"},
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    if response.status_code == 200:
        data = response.json()
        return data.get("access_token"), data.get("admin")
    return None, None


def test_get_current_admin(token):
    """Test getting current admin profile"""
    print("\n" + "=" * 50)
    print("Testing Get Current Admin Profile...")
    print("=" * 50)

    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(f"{BASE_URL}/admin/me", headers=headers)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_create_admin_without_auth():
    """Test creating admin without authentication (should fail)"""
    print("\n" + "=" * 50)
    print("Testing Create Admin Without Auth (Should Fail)...")
    print("=" * 50)

    response = requests.post(
        f"{BASE_URL}/admin/create",
        json={
            "name": "Test Admin",
            "username": "testadmin",
            "email": "test@admin.com",
            "password": "Test@123",
            "level": 5,
            "is_verified": True,
        },
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 401


def test_create_admin_with_auth(token):
    """Test creating admin with super admin auth"""
    print("\n" + "=" * 50)
    print("Testing Create Admin With Super Admin Auth...")
    print("=" * 50)

    headers = {"Authorization": f"Bearer {token}"}

    response = requests.post(
        f"{BASE_URL}/admin/create",
        headers=headers,
        json={
            "name": "Test Admin",
            "username": "testadmin2",
            "email": "test2@admin.com",
            "password": "Test@123",
            "level": 5,
            "is_verified": True,
        },
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code in [200, 201, 409]  # 409 if already exists


def test_unauthorized_access():
    """Test accessing protected endpoint without token"""
    print("\n" + "=" * 50)
    print("Testing Unauthorized Access (Should Fail)...")
    print("=" * 50)

    response = requests.get(f"{BASE_URL}/admin/me")

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 401


def test_invalid_token():
    """Test accessing with invalid token"""
    print("\n" + "=" * 50)
    print("Testing Invalid Token (Should Fail)...")
    print("=" * 50)

    headers = {"Authorization": "Bearer invalid_token_here"}

    response = requests.get(f"{BASE_URL}/admin/me", headers=headers)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 401


def run_all_tests():
    """Run all admin authentication tests"""
    print("\n")
    print("*" * 50)
    print("ADMIN AUTHENTICATION TEST SUITE")
    print("*" * 50)
    print("\n")

    results = {}

    # Test 1: Admin Login
    token, admin = test_admin_login()
    results["Admin Login"] = token is not None

    if not token:
        print("\n❌ Admin login failed. Cannot continue tests.")
        return

    # Test 2: Get Current Admin Profile
    results["Get Current Admin"] = test_get_current_admin(token)

    # Test 3: Unauthorized Access
    results["Unauthorized Access Blocked"] = test_unauthorized_access()

    # Test 4: Invalid Token
    results["Invalid Token Blocked"] = test_invalid_token()

    # Test 5: Create Admin Without Auth
    results["Create Admin Without Auth Blocked"] = test_create_admin_without_auth()

    # Test 6: Create Admin With Auth
    results["Create Admin With Auth"] = test_create_admin_with_auth(token)

    # Print Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    passed = 0
    failed = 0

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print("\n" + "-" * 50)
    print(f"Total Tests: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("-" * 50)

    if failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {failed} test(s) failed.")


if __name__ == "__main__":
    try:
        run_all_tests()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server.")
        print("Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
