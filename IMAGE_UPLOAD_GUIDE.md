# Image Upload System Documentation

## Overview

The image upload system allows users to upload images for courses, categories, and other entities. Images are stored with UUID-based filenames to prevent conflicts and ensure uniqueness.

## Features

### ✅ Implemented Features

- **UUID-based file naming** - All uploaded files get a unique UUID filename
- **File validation** - Validates file type and size before upload
- **Storage management** - Organized folder structure for different entity types
- **Automatic cleanup** - Old images are deleted when uploading new ones
- **Static file serving** - Images accessible via HTTP endpoints
- **PostgreSQL compatible** - Stores relative paths in database

### 🎯 File Specifications

- **Allowed formats**: JPG, JPEG, PNG, GIF, WEBP, SVG
- **Maximum file size**: 5MB
- **Storage location**: `storage/` directory (gitignored)
- **URL pattern**: `http://your-domain/storage/{folder}/{uuid}.{ext}`

## Architecture

### Directory Structure

```
backend/
├── storage/              # Main storage directory (gitignored)
│   ├── .gitkeep         # Ensures directory is tracked
│   ├── courses/         # Course images
│   ├── categories/      # Category images
│   ├── users/           # User profile pictures
│   └── lectures/        # Lecture content images
├── app/
│   ├── utils/
│   │   └── file_upload.py    # File upload service
│   ├── services/
│   │   └── courses.py         # Course service with image methods
│   └── routers/
│       └── courses.py         # Course endpoints including image upload
```

### Database Storage

Images are stored as **relative paths** in the database:

```
courses.image = "courses/550e8400-e29b-41d4-a716-446655440000.jpg"
```

This approach:

- ✅ Allows easy migration between environments
- ✅ Simple to change storage location
- ✅ Works with CDN integration
- ✅ PostgreSQL/MySQL compatible

## API Endpoints

### 1. Upload Course Image

```http
POST /courses/{course_id}/upload-image
Content-Type: multipart/form-data

Parameters:
  - image: file (required) - The image file to upload

Response: 200 OK
{
  "id": 1,
  "title": "Python Course",
  "image": "courses/550e8400-e29b-41d4-a716-446655440000.jpg",
  ...
}
```

### 2. Delete Course Image

```http
DELETE /courses/{course_id}/delete-image

Response: 200 OK
{
  "id": 1,
  "title": "Python Course",
  "image": null,
  ...
}
```

### 3. Access Uploaded Image

```http
GET /storage/courses/550e8400-e29b-41d4-a716-446655440000.jpg

Response: Image file
```

## Usage Examples

### Frontend - Upload Image (JavaScript/React)

```javascript
async function uploadCourseImage(courseId, imageFile) {
  const formData = new FormData();
  formData.append("image", imageFile);

  const response = await fetch(`/courses/${courseId}/upload-image`, {
    method: "POST",
    body: formData,
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await response.json();
  console.log("Image uploaded:", data.image);

  // Display image
  const imageUrl = `${baseUrl}/storage/${data.image}`;
  return imageUrl;
}
```

### Frontend - HTML Form

```html
<form id="uploadForm">
  <input type="file" name="image" accept="image/*" required />
  <button type="submit">Upload Image</button>
</form>

<script>
  document
    .getElementById("uploadForm")
    .addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(e.target);

      const response = await fetch("/courses/1/upload-image", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();
      console.log("Uploaded:", result);
    });
</script>
```

### Python - Testing with requests

```python
import requests

# Upload image
with open('course_image.jpg', 'rb') as f:
    files = {'image': f}
    response = requests.post(
        'http://localhost:8000/courses/1/upload-image',
        files=files
    )
    print(response.json())

# Access image
image_url = f"http://localhost:8000/storage/{response.json()['image']}"
```

### cURL - Command Line

```bash
# Upload image
curl -X POST "http://localhost:8000/courses/1/upload-image" \
  -H "Content-Type: multipart/form-data" \
  -F "image=@./course_image.jpg"

# Delete image
curl -X DELETE "http://localhost:8000/courses/1/delete-image"

# Download image
curl "http://localhost:8000/storage/courses/550e8400-e29b-41d4-a716-446655440000.jpg" \
  --output downloaded_image.jpg
```

## Service Layer

### FileUploadService

Location: `app/utils/file_upload.py`

#### Methods

##### `save_image(file: UploadFile, folder: str) -> tuple[str, str]`

Saves an uploaded image with UUID naming.

**Parameters:**

- `file`: The uploaded file
- `folder`: Subfolder name (e.g., 'courses', 'categories')

**Returns:**

- Tuple of `(uuid_filename, relative_path)`

**Raises:**

- `HTTPException(400)`: Invalid file type or size
- `HTTPException(500)`: Error saving file

##### `delete_image(relative_path: str) -> bool`

Deletes an image file from storage.

**Parameters:**

- `relative_path`: Relative path to the file

**Returns:**

- `True` if deleted successfully, `False` otherwise

##### `get_absolute_path(relative_path: str) -> Optional[Path]`

Gets absolute path for a stored file.

**Parameters:**

- `relative_path`: Relative path to the file

**Returns:**

- `Path` object or `None` if file doesn't exist

## Course Service Methods

### `upload_course_image(course_id: int, image_file: UploadFile) -> Optional[Course]`

Upload and attach an image to a course.

**Behavior:**

1. Validates course exists
2. Deletes old image if exists
3. Saves new image with UUID filename
4. Updates course record with new image path
5. Returns updated course

### `delete_course_image(course_id: int) -> Optional[Course]`

Delete the image attached to a course.

**Behavior:**

1. Validates course exists
2. Deletes image file from storage
3. Sets course.image to NULL
4. Returns updated course

## Error Handling

### Common Errors

#### 400 Bad Request

```json
{
  "detail": "Invalid file type. Allowed types: .jpg, .jpeg, .png, .gif, .webp, .svg"
}
```

#### 400 Bad Request - File Too Large

```json
{
  "detail": "File size exceeds maximum allowed size of 5.0MB"
}
```

#### 404 Not Found

```json
{
  "detail": "Course not found"
}
```

#### 500 Internal Server Error

```json
{
  "detail": "Error saving file: ..."
}
```

## Security Considerations

### ✅ Implemented Security

- **File type validation** - Only allowed image types
- **File size limits** - Maximum 5MB per file
- **UUID filenames** - Prevents path traversal attacks
- **Organized folders** - Separate folders per entity type

### 🔒 Recommended Additional Security

1. **Authentication** - Add authentication to upload endpoints
2. **Rate limiting** - Limit upload requests per user
3. **Image scanning** - Scan for malware in uploaded files
4. **Compression** - Automatically compress large images
5. **CDN integration** - Serve images from CDN for better performance

## Environment Configuration

### Production Recommendations

1. **Use Environment Variables**

```python
# In config.py
STORAGE_PATH = os.getenv('STORAGE_PATH', 'storage')
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 5 * 1024 * 1024))
```

2. **External Storage (S3, Google Cloud Storage)**

```python
# Modify file_upload.py to use S3
import boto3

class S3FileUploadService:
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.bucket = os.getenv('S3_BUCKET')

    async def save_image(self, file: UploadFile, folder: str):
        # Upload to S3 instead of local storage
        pass
```

3. **CDN Integration**

```python
# Return CDN URL instead of local path
def get_image_url(relative_path: str) -> str:
    cdn_base = os.getenv('CDN_BASE_URL')
    return f"{cdn_base}/{relative_path}"
```

## Testing

### Unit Tests Example

```python
import pytest
from fastapi.testclient import TestClient
from io import BytesIO

def test_upload_course_image(client: TestClient):
    # Create a fake image file
    fake_image = BytesIO(b"fake image content")
    fake_image.name = "test.jpg"

    response = client.post(
        "/courses/1/upload-image",
        files={"image": ("test.jpg", fake_image, "image/jpeg")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["image"].startswith("courses/")
    assert data["image"].endswith(".jpg")

def test_upload_invalid_file_type(client: TestClient):
    fake_file = BytesIO(b"fake content")
    fake_file.name = "test.txt"

    response = client.post(
        "/courses/1/upload-image",
        files={"image": ("test.txt", fake_file, "text/plain")}
    )

    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]
```

## Migration Guide

### From URL Storage to File Storage

If you previously stored external URLs, you can migrate:

```python
# Migration script
from app.models.courses import Course
from app.core.database import SessionLocal

db = SessionLocal()
courses = db.query(Course).filter(Course.image.isnot(None)).all()

for course in courses:
    # Check if image is external URL
    if course.image.startswith('http'):
        print(f"Course {course.id} has external URL: {course.image}")
        # Optionally download and convert to local storage
    else:
        print(f"Course {course.id} already uses local storage: {course.image}")

db.close()
```

## Troubleshooting

### Issue: Images not accessible via /storage/

**Solution:** Ensure StaticFiles is mounted correctly in main.py

```python
app.mount("/storage", StaticFiles(directory="storage"), name="storage")
```

### Issue: Permission denied when saving files

**Solution:** Check directory permissions

```bash
chmod 755 storage/
chmod 755 storage/courses/
```

### Issue: Old images not being deleted

**Solution:** Check file_upload_service.delete_image() is called before upload

### Issue: Large files failing

**Solution:** Increase max file size in file_upload.py

```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
```

## Future Enhancements

### Planned Features

- [ ] Image resizing/thumbnails
- [ ] Multiple image uploads
- [ ] Image gallery for courses
- [ ] Automatic image optimization
- [ ] S3/Cloud storage integration
- [ ] Image cropping/editing API
- [ ] WebP automatic conversion
- [ ] Video upload support

## Summary

The image upload system is now fully functional with:

- ✅ UUID-based file naming
- ✅ Validation and security
- ✅ Storage management
- ✅ PostgreSQL compatibility
- ✅ RESTful API endpoints
- ✅ Static file serving

All uploaded images are stored in the `storage/` directory and accessible via the `/storage/` URL path.
