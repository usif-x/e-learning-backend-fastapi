"""
Test script for image upload functionality
Run this after starting the server to test image upload endpoints
"""

from io import BytesIO

import requests
from PIL import Image

BASE_URL = "http://localhost:8000"


def create_test_image():
    """Create a test image in memory"""
    # Create a simple 200x200 red image
    img = Image.new("RGB", (200, 200), color="red")
    img_bytes = BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)
    return img_bytes


def test_upload_image(course_id: int = 1):
    """Test uploading an image to a course"""
    print(f"\n📤 Testing image upload for course {course_id}...")

    # Create test image
    image_file = create_test_image()

    # Upload
    files = {"image": ("test_image.jpg", image_file, "image/jpeg")}
    response = requests.post(
        f"{BASE_URL}/courses/{course_id}/upload-image", files=files
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Upload successful!")
        print(f"   Image path: {data.get('image')}")
        print(f"   Access at: {BASE_URL}/storage/{data.get('image')}")
        return data.get("image")
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return None


def test_access_image(image_path: str):
    """Test accessing an uploaded image"""
    if not image_path:
        print("⚠️  No image path provided, skipping access test")
        return

    print(f"\n🔍 Testing image access...")
    response = requests.get(f"{BASE_URL}/storage/{image_path}")

    if response.status_code == 200:
        print(f"✅ Image accessible!")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        print(f"   Size: {len(response.content)} bytes")
    else:
        print(f"❌ Access failed: {response.status_code}")


def test_delete_image(course_id: int = 1):
    """Test deleting a course image"""
    print(f"\n🗑️  Testing image deletion for course {course_id}...")

    response = requests.delete(f"{BASE_URL}/courses/{course_id}/delete-image")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Deletion successful!")
        print(f"   Image field: {data.get('image')}")
    else:
        print(f"❌ Deletion failed: {response.status_code}")
        print(f"   Error: {response.text}")


def test_invalid_file():
    """Test uploading an invalid file type"""
    print(f"\n🚫 Testing invalid file upload...")

    # Create a text file
    text_file = BytesIO(b"This is not an image")
    files = {"image": ("test.txt", text_file, "text/plain")}

    response = requests.post(f"{BASE_URL}/courses/1/upload-image", files=files)

    if response.status_code == 400:
        print(f"✅ Correctly rejected invalid file!")
        print(f"   Error message: {response.json().get('detail')}")
    else:
        print(f"❌ Should have rejected invalid file!")


def test_large_file():
    """Test uploading a file that's too large"""
    print(f"\n📏 Testing oversized file upload...")

    # Create a 6MB file (over the 5MB limit)
    large_data = b"x" * (6 * 1024 * 1024)
    large_file = BytesIO(large_data)
    files = {"image": ("large.jpg", large_file, "image/jpeg")}

    response = requests.post(f"{BASE_URL}/courses/1/upload-image", files=files)

    if response.status_code == 400:
        print(f"✅ Correctly rejected oversized file!")
        print(f"   Error message: {response.json().get('detail')}")
    else:
        print(f"❌ Should have rejected oversized file!")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("🧪 IMAGE UPLOAD SYSTEM TESTS")
    print("=" * 60)

    try:
        # Test 1: Upload valid image
        image_path = test_upload_image(course_id=1)

        # Test 2: Access uploaded image
        if image_path:
            test_access_image(image_path)

        # Test 3: Upload another image (replaces the first one)
        image_path2 = test_upload_image(course_id=1)

        # Test 4: Delete image
        test_delete_image(course_id=1)

        # Test 5: Invalid file type
        test_invalid_file()

        # Test 6: File too large
        test_large_file()

        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server!")
        print("   Make sure the server is running at", BASE_URL)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    # Check if PIL is installed
    try:
        from PIL import Image
    except ImportError:
        print("⚠️  Pillow not installed. Installing...")
        print("   Run: pip install Pillow")
        exit(1)

    run_all_tests()
