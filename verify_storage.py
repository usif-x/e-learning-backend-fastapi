import requests
from io import BytesIO
from PIL import Image
import sys

BASE_URL = "http://localhost:8000"
TOKEN = None

def login():
    """Login as admin to get token"""
    global TOKEN
    try:
        print("🔑 Logging in...")
        response = requests.post(
            f"{BASE_URL}/auth/admin/login",
            json={"username_or_email": "admin@example.com", "password": "Admin@123"},
        )
        if response.status_code == 200:
            TOKEN = response.json().get("access_token")
            print("✅ Login successful")
            return True
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False

def get_headers():
    return {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

def create_test_image():
    """Create a test image in memory"""
    img = Image.new("RGB", (200, 200), color="red")
    img_bytes = BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)
    return img_bytes

def create_course():
    """Create a test course"""
    print(f"\n📚 Creating test course...")
    try:
        response = requests.post(
            f"{BASE_URL}/courses/",
            json={"name": "Test Course", "price": 0, "is_free": True},
            headers=get_headers()
        )
        if response.status_code == 201:
            data = response.json()
            print(f"✅ Course created: ID {data.get('id')}")
            return data.get('id')
        else:
            print(f"❌ Course creation failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Course creation error: {e}")
        return None

def test_upload_image(course_id):
    """Test uploading an image"""
    print(f"\n📤 Testing image upload to course {course_id}...")
    image_file = create_test_image()
    files = {"image": ("test_image.jpg", image_file, "image/jpeg")}
    
    try:
        response = requests.post(
            f"{BASE_URL}/courses/{course_id}/upload-image", 
            files=files, 
            headers=get_headers()
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Upload successful!")
            print(f"   Image path: {data.get('image')}")
            return data.get("image")
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

def run_test():
    if not login():
        sys.exit(1)
    
    course_id = create_course()
    if not course_id:
        sys.exit(1)
        
    image_path = test_upload_image(course_id)
    if image_path:
        print("\n✅ Verification passed: Image uploaded successfully.")
    else:
        print("\n❌ Verification failed.")
        sys.exit(1)

if __name__ == "__main__":
    run_test()
