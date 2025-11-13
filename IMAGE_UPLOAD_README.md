# Image Upload Quick Start Guide

## 🚀 Quick Setup

### 1. Install Dependencies

All required dependencies are already in `requirements.txt`. No additional packages needed!

### 2. Directory Structure Created

```
backend/
├── storage/              # ✅ Created automatically
│   ├── courses/         # ✅ Will be created on first upload
│   ├── categories/      # ✅ Will be created on first upload
│   └── users/           # ✅ Will be created on first upload
```

### 3. Start the Server

```bash
python main.py --env dev
```

The storage directory will be mounted at `/storage/` endpoint.

## 📝 Quick Test

### Using cURL

```bash
# Upload an image
curl -X POST "http://localhost:8000/courses/1/upload-image" \
  -F "image=@path/to/your/image.jpg"

# Response:
{
  "id": 1,
  "title": "Course Name",
  "image": "courses/550e8400-e29b-41d4-a716-446655440000.jpg",
  ...
}

# Access the uploaded image
curl "http://localhost:8000/storage/courses/550e8400-e29b-41d4-a716-446655440000.jpg" \
  --output downloaded.jpg

# Delete the image
curl -X DELETE "http://localhost:8000/courses/1/delete-image"
```

### Using Python Script

```bash
# Install test dependencies (optional)
pip install Pillow requests

# Run test script
python test_image_upload.py
```

### Using Postman or Thunder Client

1. Create a POST request to `http://localhost:8000/courses/1/upload-image`
2. Select Body → form-data
3. Add key: `image`, type: File
4. Choose an image file
5. Send!

## 🎯 API Endpoints

### Upload Image

```
POST /courses/{course_id}/upload-image
Content-Type: multipart/form-data
Body: image (file)
```

### Delete Image

```
DELETE /courses/{course_id}/delete-image
```

### Access Image

```
GET /storage/{folder}/{uuid}.{ext}
Example: GET /storage/courses/550e8400-e29b-41d4-a716-446655440000.jpg
```

## ✅ Features

- ✅ UUID-based unique filenames
- ✅ Automatic old image cleanup
- ✅ File validation (type & size)
- ✅ PostgreSQL compatible
- ✅ Organized folder structure
- ✅ Static file serving

## 📋 File Constraints

- **Max Size**: 5MB
- **Allowed Types**: .jpg, .jpeg, .png, .gif, .webp, .svg
- **Storage**: `storage/` directory (gitignored)

## 🔧 How It Works

1. **Upload**: User sends image file → Backend validates → Generates UUID → Saves to `storage/courses/`
2. **Database**: Stores relative path: `"courses/uuid.jpg"`
3. **Access**: Image served at `/storage/courses/uuid.jpg`
4. **Update**: New upload automatically deletes old image

## 📚 More Info

See `IMAGE_UPLOAD_GUIDE.md` for complete documentation.

## ✨ Example Frontend Code

### React/JavaScript

```javascript
const uploadImage = async (courseId, file) => {
  const formData = new FormData();
  formData.append("image", file);

  const response = await fetch(`/courses/${courseId}/upload-image`, {
    method: "POST",
    body: formData,
  });

  const data = await response.json();
  return `/storage/${data.image}`; // Use this URL to display
};
```

### HTML

```html
<input type="file" id="imageInput" accept="image/*" />
<img id="preview" src="" alt="Course Image" />

<script>
  document
    .getElementById("imageInput")
    .addEventListener("change", async (e) => {
      const file = e.target.files[0];
      const formData = new FormData();
      formData.append("image", file);

      const res = await fetch("/courses/1/upload-image", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      document.getElementById("preview").src = `/storage/${data.image}`;
    });
</script>
```

## 🎉 You're All Set!

The image upload system is ready to use. Just start your server and start uploading!
