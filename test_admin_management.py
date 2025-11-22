"""
Test Admin Management Functionality
"""

import json

import requests

BASE_URL = "http://localhost:8000"


def test_admin_management():
    """Test comprehensive admin management functionality"""
    print("=" * 60)
    print("Testing Admin Management Functionality")
    print("=" * 60)

    # Step 1: Login as super admin
    print("\n1. Logging in as super admin...")
    response = requests.post(
        f"{BASE_URL}/auth/admin/login",
        json={"username_or_email": "superadmin", "password": "SuperAdmin@123"},
    )

    if response.status_code != 200:
        print(f"❌ Failed to login as super admin: {response.status_code}")
        print(f"Response: {response.json()}")
        return False

    super_admin_token = response.json().get("access_token")
    super_admin_data = response.json().get("admin")
    print(
        f"✅ Logged in as super admin: {super_admin_data['username']} (Level: {super_admin_data['level']})"
    )

    headers = {"Authorization": f"Bearer {super_admin_token}"}

    # Step 2: Create a new admin
    print("\n2. Creating a new admin...")
    new_admin_data = {
        "name": "Test Admin",
        "username": "testadmin",
        "email": "testadmin@example.com",
        "password": "TestAdmin@123",
        "telegram_id": None,
        "level": 1,
        "is_verified": True,
    }

    response = requests.post(
        f"{BASE_URL}/admin/create", json=new_admin_data, headers=headers
    )

    if response.status_code != 201:
        print(f"❌ Failed to create admin: {response.status_code}")
        print(f"Response: {response.json()}")
        return False

    created_admin = response.json().get("admin")
    admin_id = created_admin["id"]
    print(f"✅ Created admin: {created_admin['username']} (ID: {admin_id})")

    # Step 3: List all admins
    print("\n3. Listing all admins...")
    response = requests.get(f"{BASE_URL}/admin/list", headers=headers)

    if response.status_code != 200:
        print(f"❌ Failed to list admins: {response.status_code}")
        print(f"Response: {response.json()}")
        return False

    admins_list = response.json()
    print(f"✅ Found {admins_list['total']} admins")
    print(f"Current page: {admins_list['page']}")

    # Step 4: Get specific admin by ID
    print(f"\n4. Getting admin by ID ({admin_id})...")
    response = requests.get(f"{BASE_URL}/admin/{admin_id}", headers=headers)

    if response.status_code != 200:
        print(f"❌ Failed to get admin by ID: {response.status_code}")
        print(f"Response: {response.json()}")
        return False

    admin_details = response.json()
    print(f"✅ Retrieved admin: {admin_details['username']} - {admin_details['email']}")

    # Step 5: Update admin details
    print(f"\n5. Updating admin details...")
    update_data = {
        "name": "Updated Test Admin",
        "email": "updated_testadmin@example.com",
    }

    response = requests.put(
        f"{BASE_URL}/admin/{admin_id}", json=update_data, headers=headers
    )

    if response.status_code != 200:
        print(f"❌ Failed to update admin: {response.status_code}")
        print(f"Response: {response.json()}")
        return False

    updated_admin = response.json()
    print(f"✅ Updated admin name to: {updated_admin['name']}")
    print(f"✅ Updated admin email to: {updated_admin['email']}")

    # Step 6: Reset admin password
    print(f"\n6. Resetting admin password...")
    response = requests.post(
        f"{BASE_URL}/admin/{admin_id}/reset-password?new_password=NewPassword@123",
        headers=headers,
    )

    if response.status_code != 200:
        print(f"❌ Failed to reset password: {response.status_code}")
        print(f"Response: {response.json()}")
        return False

    print("✅ Password reset successfully")

    # Step 7: Test regular admin permissions
    print("\n7. Testing regular admin permissions...")

    # Login as the created admin
    response = requests.post(
        f"{BASE_URL}/auth/admin/login",
        json={"username_or_email": "testadmin", "password": "NewPassword@123"},
    )

    if response.status_code != 200:
        print(f"❌ Failed to login as regular admin: {response.status_code}")
        print(f"Response: {response.json()}")
        return False

    regular_admin_token = response.json().get("access_token")
    regular_headers = {"Authorization": f"Bearer {regular_admin_token}"}

    # Regular admin should be able to update their own profile
    update_self_data = {"name": "Self Updated Admin"}
    response = requests.put(
        f"{BASE_URL}/admin/{admin_id}", json=update_self_data, headers=regular_headers
    )

    if response.status_code != 200:
        print(f"❌ Regular admin failed to update own profile: {response.status_code}")
        print(f"Response: {response.json()}")
        return False

    print("✅ Regular admin can update own profile")

    # Regular admin should NOT be able to list all admins
    response = requests.get(f"{BASE_URL}/admin/list", headers=regular_headers)

    if response.status_code != 403:
        print(
            f"❌ Regular admin should not be able to list admins: {response.status_code}"
        )
        return False

    print("✅ Regular admin cannot list all admins (403 Forbidden)")

    # Regular admin should NOT be able to create new admins
    new_admin_data_2 = {
        "name": "Another Admin",
        "username": "anotheradmin",
        "email": "another@example.com",
        "password": "Another@123",
        "level": 1,
        "is_verified": True,
    }

    response = requests.post(
        f"{BASE_URL}/admin/create", json=new_admin_data_2, headers=regular_headers
    )

    if response.status_code != 403:
        print(
            f"❌ Regular admin should not be able to create admins: {response.status_code}"
        )
        return False

    print("✅ Regular admin cannot create new admins (403 Forbidden)")

    # Step 8: Delete the test admin (back to super admin)
    print(f"\n8. Deleting test admin...")
    response = requests.delete(f"{BASE_URL}/admin/{admin_id}", headers=headers)

    if response.status_code != 200:
        print(f"❌ Failed to delete admin: {response.status_code}")
        print(f"Response: {response.json()}")
        return False

    print("✅ Test admin deleted successfully")

    print("\n" + "=" * 60)
    print("🎉 All admin management tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    test_admin_management()
