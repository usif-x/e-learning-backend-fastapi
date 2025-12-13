# E-Learning Platform Backend

A comprehensive FastAPI-based backend for an educational platform with AI-powered features, community engagement, and advanced learning management capabilities.

## 🌟 Features

### Core Functionality

- **User Management**: Registration, authentication, and profile management
- **Course Management**: Create, organize, and manage educational courses
- **Lecture System**: Support for video lectures, content, and materials
- **Category Organization**: Hierarchical category system for content organization
- **Admin Panel**: Comprehensive admin controls and management tools

### AI-Powered Features

- **AI Question Generation**: Generate educational questions using DeepSeek AI
  - Multiple question types: Multiple Choice, True/False, Essay, Mixed
  - Difficulty levels: Easy, Medium, Hard
  - Smart question distribution (70% Standard, 20% Critical Thinking, 10% Linking)
  - Bilingual explanations (English & Egyptian Arabic)
- **PDF Content Analysis**: Extract and explain PDF content with OCR support
- **Intelligent Content Summarization**: AI-powered content summarization
- **Topic Explanations**: Generate comprehensive topic explanations

### Advanced PDF Processing

- **Text Extraction**: Extract text from PDFs using PyPDF2
- **OCR Support**: Automatic OCR for image-based PDFs using Tesseract
  - Supports English and Arabic languages
  - Smart detection of pages requiring OCR (<5 words threshold)
  - Automatic page filtering (skip intro, conclusion, references)
- **Question Generation from PDFs**: Generate quizzes directly from PDF content

### Community Features

- **Posts & Discussions**: Create and share educational content
- **Comments & Reactions**: Engage with community content
- **Post Moderation**: Admin controls for content moderation
- **Media Upload**: Support for images and attachments in posts
- **Community Management**: Admin-controlled communities with member management

### Practice & Assessment

- **Practice Quizzes**: Interactive practice questions
- **Quiz Attempts**: Track and manage quiz attempts
- **Question Banks**: Store and manage generated questions
- **PDF Question Export**: Generate formatted PDF files from questions

### Analytics & Tracking

- **User Analytics**: Track user engagement and progress
- **Daily Usage**: Monitor daily platform usage
- **Learning Progress**: Track course and lecture completion

### Additional Features

- **Telegram Integration**: Telegram authentication support
- **File Upload**: Secure file upload for courses, lectures, and user profiles
- **Notifications**: Real-time notification system
- **Image Processing**: Support for course thumbnails and user avatars
- **Rate Limiting**: API rate limiting for security
- **Caching**: Redis-based caching for performance

## 🛠️ Tech Stack

### Core

- **FastAPI**: Modern, fast web framework for building APIs
- **Python 3.9+**: Programming language
- **PostgreSQL**: Primary database
- **SQLAlchemy**: ORM for database operations
- **Alembic**: Database migrations

### AI & ML

- **DeepSeek AI**: AI model for question generation and content analysis
- **PyTesseract**: OCR engine for image-based PDFs
- **pdf2image**: Convert PDF pages to images
- **PyPDF2**: PDF text extraction

### Authentication & Security

- **JWT**: Token-based authentication
- **Passlib**: Password hashing
- **Python-Jose**: JWT token handling

### File Processing

- **Pillow (PIL)**: Image processing
- **ReportLab**: PDF generation for quizzes
- **python-multipart**: File upload support

### Other Libraries

- **httpx**: Async HTTP client for AI API calls
- **python-dotenv**: Environment variable management
- **Pydantic**: Data validation

## 📋 Prerequisites

- Python 3.9 or higher
- PostgreSQL 12 or higher
- Tesseract OCR engine
- Redis (optional, for caching)

## 🚀 Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd backend
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Tesseract OCR

**macOS:**

```bash
brew install tesseract
brew install tesseract-lang  # For Arabic support
```

**Ubuntu/Debian:**

```bash
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-ara  # For Arabic
```

**Windows:**
Download and install from [Tesseract GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

### 5. Set up environment variables

Create a `.env` file in the backend directory:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/elearning

# JWT Secret
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Configuration
AI_API_KEY=your-deepseek-api-key
AI_API_ENDPOINT=https://api.deepseek.com/v1/chat/completions
AI_MODEL=deepseek-chat



### Other Env ###
```

### 6. Run database migrations

```bash
alembic upgrade head
```

### 7. Create initial admin user

```bash
python -c "from app.services.admin import create_initial_admin; create_initial_admin()"
```

## 🏃 Running the Application

### Development

```bash
python main.py dev + ( With Reload add : --reload )
```

### Production

```bash
python main.py prod
```

The API will be available at `http://localhost:8000`

API Documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 📁 Project Structure

```
backend/
├── app/
│   ├── core/           # Core configurations
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   └── ...
│   ├── models/         # SQLAlchemy models
│   │   ├── user.py
│   │   ├── course.py
│   │   ├── lecture.py
│   │   └── ...
│   ├── schemas/        # Pydantic schemas
│   │   ├── user.py
│   │   ├── course.py
│   │   └── ...
│   ├── routers/        # API endpoints
│   │   ├── auth.py
│   │   ├── course.py
│   │   ├── ai.py
│   │   └── ...
│   ├── services/       # Business logic
│   │   ├── auth.py
│   │   ├── course.py
│   │   └── ...
│   └── utils/          # Utility functions
│       ├── ai.py
│       ├── file_upload.py
│       └── ...
├── migrations/         # Alembic migrations
├── storage/           # Uploaded files storage
│   ├── courses/
│   ├── lectures/
│   ├── users/
│   └── ...
├── logs/              # Application logs
├── main.py            # Application entry point
├── requirements.txt   # Python dependencies
└── alembic.ini       # Alembic configuration
```

## 🔑 API Endpoints

### Authentication

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `POST /api/auth/telegram` - Telegram authentication
- `POST /api/auth/verify-email` - Verify email
- `POST /api/auth/reset-password` - Reset password

### Courses

- `GET /api/courses` - List all courses
- `POST /api/courses` - Create course (Admin)
- `GET /api/courses/{id}` - Get course details
- `PUT /api/courses/{id}` - Update course (Admin)
- `DELETE /api/courses/{id}` - Delete course (Admin)

### AI Features

- `POST /api/ai/generate-questions` - Generate questions from topic
- `POST /api/ai/generate-questions-pdf` - Generate questions from PDF
- `POST /api/ai/explain-pdf` - Explain PDF content
- `POST /api/ai/explain-topic` - Explain a topic

### Community

- `GET /api/community` - List communities
- `POST /api/community` - Create community (Admin)
- `GET /api/community/{id}/posts` - Get community posts
- `POST /api/community/{id}/posts` - Create post
- `POST /api/community/posts/{id}/comments` - Add comment
- `POST /api/community/posts/{id}/react` - React to post

### Admin

- `POST /api/admin/login` - Admin login
- `GET /api/admin/users` - List users
- `GET /api/admin/analytics` - Get analytics
- `POST /api/admin/moderate` - Moderate content

## 🧪 Testing

Run tests:

```bash
pytest
```

Run specific test file:

```bash
pytest test_admin_auth.py
```

## 📝 AI Question Generation

The platform uses DeepSeek AI for intelligent question generation with the following features:

### Question Distribution

- **70% Standard Questions**: Direct knowledge assessment
- **20% Critical Thinking**: Higher-order reasoning
- **10% Linking Questions**: Concept integration

### Supported Question Types

- Multiple Choice (4 options)
- True/False
- Essay/Short Answer
- Mixed (combination of types)

### Difficulty Levels

- **Easy**: Basic recall and definitions
- **Medium**: Understanding and application
- **Hard**: Complex analysis and synthesis

### Bilingual Support

- Questions in English
- Explanations in both English and Egyptian Arabic
- Medical terms preserved in English

## 📄 PDF Processing Features

### OCR Support

- Automatic detection of image-based PDFs
- OCR for pages with <5 words
- Support for English and Arabic text
- Smart page filtering

### Content Extraction

- Text extraction using PyPDF2
- Fallback to OCR for images
- Page-by-page processing
- Batch processing for efficiency

### Question Generation

- Generate quizzes from PDF content
- Contextual question creation
- Support for all question types
- Content-based explanations

## 🔒 Security Features

- JWT-based authentication
- Password hashing with bcrypt
- Rate limiting on API endpoints
- File upload validation
- SQL injection prevention (SQLAlchemy ORM)
- CORS configuration
- Environment-based configuration

## 🚀 Deployment

### Using Docker (Recommended)

```bash
docker-compose up -d
```

### Manual Deployment

1. Set up PostgreSQL database
2. Configure environment variables
3. Run migrations: `alembic upgrade head`
4. Start with production server: `uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4`

### Environment Variables for Production

- Set `DEBUG=False`
- Use strong `SECRET_KEY`
- Configure proper CORS origins
- Set up SSL/TLS certificates
- Use a reverse proxy (Nginx/Caddy)

## 📊 Database Migrations

Create a new migration:

```bash
alembic revision --autogenerate -m "Description"
```

Apply migrations:

```bash
alembic upgrade head
```

Rollback migration:

```bash
alembic downgrade -1
```

## 📧 Support

For support, email yousseifmuhammed@gmail.com or create an issue in the repository.

## 🔄 Version History

- **v1.0.0** - Initial release with core features
- Features: User management, courses, AI questions, community, PDF processing

---

**Built with ❤️ for education**
