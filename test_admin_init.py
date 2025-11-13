"""
Test script to verify super admin initialization
Run this to test the admin initialization without starting the full server
"""

from app.core.database import SessionLocal
from app.core.init import initialize_application
from app.models.admin import Admin


def test_admin_initialization():
    """Test the admin initialization process"""
    print("\n" + "=" * 60)
    print("Testing Super Admin Initialization")
    print("=" * 60)

    db = SessionLocal()
    try:
        # Check admins before
        admin_count_before = db.query(Admin).count()
        print(f"\n📊 Admins in database before: {admin_count_before}")

        # Run initialization
        print("\n🔄 Running initialization...")
        initialize_application(db)

        # Check admins after
        admin_count_after = db.query(Admin).count()
        print(f"\n📊 Admins in database after: {admin_count_after}")

        # Show all admins
        admins = db.query(Admin).all()
        if admins:
            print("\n👥 Current Admins:")
            print("-" * 60)
            for admin in admins:
                print(f"ID: {admin.id}")
                print(f"Name: {admin.name}")
                print(f"Username: {admin.username}")
                print(f"Email: {admin.email}")
                print(f"Level: {admin.level}")
                print(f"Verified: {admin.is_verified}")
                print("-" * 60)

        print("\n✅ Test completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    test_admin_initialization()
