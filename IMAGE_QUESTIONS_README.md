# Image-Based Question Generation from PDFs

## Overview

This feature extracts diagrams, charts, and labeled images from PDFs, uses OCR to detect text labels, removes the text from the images, and generates educational questions that test visual comprehension.

## Key Features

✅ **Automatic Image Extraction** - Extracts meaningful images from PDFs  
✅ **OCR Text Detection** - Detects labels and annotations in images  
✅ **Text Removal** - Hides text from images to test comprehension  
✅ **Smart Page Filtering** - Skips intro/conclusion/reference pages  
✅ **Compressed Storage** - Optimized base64 encoding for database  
✅ **Context-Aware Questions** - Uses both image text and page content  
✅ **No Vision Model Required** - Works with text-only AI models

## How It Works

### 1. Image Processing Pipeline

```
PDF File → Extract Images → OCR Text Detection → Remove Text → Compress Image
                                    ↓
                    Generate Questions Using:
                    - Image Text (OCR)
                    - Full Page Context
                    - Difficulty Level
```

### 2. Question Generation

The AI generates questions that:

- Reference specific image labels/elements
- Test understanding of visual relationships
- Use page context for richer questions
- Include 4 plausible multiple-choice options
- Provide detailed explanations in English and Arabic

### 3. Database Storage

Questions are stored with:

- `question_type`: "image"
- `image`: Base64 encoded image (compressed)
- `question_text`: The question referencing the image
- `options`: Multiple choice options
- `correct_answer`: The correct option
- `content_page_number`: Source page number

## Usage

### Method 1: From UploadFile (API Endpoint)

```python
from fastapi import UploadFile
from app.utils.ai import ai_service

async def generate_from_upload(file: UploadFile):
    questions = await ai_service.generate_questions_from_pdf_images(
        file=file,
        difficulty="medium",
        questions_per_image=1,  # Questions per image
        max_size=600,           # Max image dimension (pixels)
        quality=40              # JPEG quality (1-100)
    )
    return questions
```

### Method 2: From File Path (Background Tasks)

```python
from app.utils.ai import ai_service

async def generate_from_path(pdf_path: str):
    questions = await ai_service.generate_questions_from_pdf_path_images(
        pdf_path=pdf_path,
        difficulty="medium",
        questions_per_image=1,
        max_size=600,
        quality=40
    )
    return questions
```

## Response Format

```json
[
  {
    "question_type": "image",
    "question_category": "standard",
    "question_text": "According to the diagram, what structure is labeled as 'Nuclear membrane'?",
    "image": "/9j/4AAQSkZJRgABA...",
    "options": [
      "The outer boundary of the nucleus",
      "The inner chromatin material",
      "The nucleolus structure",
      "The nuclear pores"
    ],
    "correct_answer": "The outer boundary of the nucleus",
    "explanation": "The nuclear membrane (envelope) is the double-walled membrane that forms the outer boundary of the nucleus.",
    "explanation_ar": "الـ nuclear membrane (الغلاف النووي) هو الغشاء المزدوج اللي بيشكل الحدود الخارجية للنواة",
    "content_page_number": 35
  }
]
```

## Configuration Parameters

### Image Processing

| Parameter    | Default | Description                                       |
| ------------ | ------- | ------------------------------------------------- |
| `max_size`   | 600     | Maximum dimension (width/height) in pixels        |
| `quality`    | 40      | JPEG compression quality (1-100, lower = smaller) |
| `min_width`  | 100     | Minimum image width to process                    |
| `min_height` | 100     | Minimum image height to process                   |

### Question Generation

| Parameter             | Default  | Description                             |
| --------------------- | -------- | --------------------------------------- |
| `difficulty`          | "medium" | Question difficulty: easy, medium, hard |
| `questions_per_image` | 1        | Number of questions per image           |

## Page Filtering

The system automatically skips:

- ✗ Title pages (first page with <50 words)
- ✗ Thank you/conclusion pages
- ✗ Reference/bibliography pages
- ✗ Table of contents
- ✗ Pages with <5 words
- ✗ Pages with professor/author information

This ensures questions are generated only from meaningful content pages.

## Image Filtering

The system skips:

- ✗ Images with transparency (likely icons/logos)
- ✗ Very small images (<100x100 pixels)
- ✗ Images with no detectable text

## Database Integration

### Adding to Your Schema

1. **Update Question Model** to support image type:

```python
# app/models/practice_quiz.py
class PracticeQuiz(Base):
    __tablename__ = "practice_quiz"

    id = Column(Integer, primary_key=True)
    question_type = Column(String)  # "image", "multiple_choice", etc.
    question_text = Column(Text)
    image = Column(Text, nullable=True)  # Base64 encoded image
    options = Column(JSON)
    correct_answer = Column(String)
    explanation = Column(Text)
    explanation_ar = Column(Text)
    content_page_number = Column(Integer, nullable=True)
    # ... other fields
```

2. **Create Migration**:

```bash
alembic revision -m "add_image_support_to_questions"
```

3. **Migration Script**:

```python
def upgrade():
    # Add image column if it doesn't exist
    op.add_column('practice_quiz',
        sa.Column('image', sa.Text(), nullable=True))

    # Update question_type enum if needed
    op.execute("""
        ALTER TYPE question_type_enum
        ADD VALUE IF NOT EXISTS 'image'
    """)

def downgrade():
    op.drop_column('practice_quiz', 'image')
```

### Saving Questions

```python
from app.models.practice_quiz import PracticeQuiz
from sqlalchemy.orm import Session

async def save_image_questions(
    db: Session,
    questions: list,
    quiz_source_id: int
):
    """Save image-based questions to database"""

    for q in questions:
        new_question = PracticeQuiz(
            quiz_source_id=quiz_source_id,
            question_type="image",
            question_category=q["question_category"],
            question_text=q["question_text"],
            image=q["image"],  # Base64 encoded
            options=q["options"],
            correct_answer=q["correct_answer"],
            explanation=q["explanation"],
            explanation_ar=q["explanation_ar"],
            content_page_number=q["content_page_number"],
        )
        db.add(new_question)

    db.commit()
```

## API Endpoint Example

```python
from fastapi import APIRouter, UploadFile, Depends
from sqlalchemy.orm import Session
from app.utils.ai import ai_service
from app.core.dependencies import get_db

router = APIRouter()

@router.post("/generate-image-questions")
async def generate_image_questions(
    file: UploadFile,
    quiz_source_id: int,
    difficulty: str = "medium",
    db: Session = Depends(get_db)
):
    """Generate questions from PDF images"""

    # Generate questions
    questions = await ai_service.generate_questions_from_pdf_images(
        file=file,
        difficulty=difficulty,
        questions_per_image=1
    )

    # Save to database
    await save_image_questions(db, questions, quiz_source_id)

    return {
        "success": True,
        "questions_generated": len(questions),
        "questions": questions
    }
```

## Frontend Display

### Decoding and Displaying Images

```javascript
// React/Vue component example
function ImageQuestion({ question }) {
  const imageUrl = `data:image/jpeg;base64,${question.image}`;

  return (
    <div className="image-question">
      <img
        src={imageUrl}
        alt="Question diagram"
        style={{ maxWidth: "100%", height: "auto" }}
      />
      <h3>{question.question_text}</h3>
      <div className="options">
        {question.options.map((option, idx) => (
          <button key={idx}>{option}</button>
        ))}
      </div>
    </div>
  );
}
```

## Performance Optimization

### Image Size Optimization

The default settings (600px, 40% quality) produce:

- **Average size**: 20-40 KB per image (base64)
- **Compression ratio**: ~75% smaller than original
- **Quality**: Sufficient for educational diagrams

### Batch Processing

For large PDFs, process in batches:

```python
async def process_large_pdf(pdf_path: str):
    """Process PDF in batches to avoid timeouts"""

    all_questions = []
    batch_size = 10  # Process 10 pages at a time

    # Implement pagination logic here
    # ...

    return all_questions
```

## Troubleshooting

### Common Issues

**1. OCR Not Detecting Text**

- Ensure Tesseract is installed: `brew install tesseract` (macOS)
- Install language data: `brew install tesseract-lang`

**2. Large Image Sizes**

- Reduce `max_size` parameter (e.g., 400)
- Lower `quality` parameter (e.g., 30)
- Convert to grayscale (already done by default)

**3. No Questions Generated**

- Check if images contain text (OCR requirement)
- Verify pages aren't being filtered out
- Check logs for specific errors

**4. Timeout on Large PDFs**

- Use `generate_questions_from_pdf_path_images` in background task
- Process fewer `questions_per_image`
- Implement batch processing

## Testing

Run the example script:

```bash
python example_image_questions.py
```

This will:

1. Process a PDF file
2. Extract and process images
3. Generate questions
4. Save to JSON file
5. Show database storage example

## Dependencies

Required Python packages (already in requirements.txt):

- `PyMuPDF` (fitz) - PDF processing
- `pytesseract` - OCR text detection
- `Pillow` (PIL) - Image processing
- `openai` - AI API client

System dependencies:

- Tesseract OCR engine

## Best Practices

1. ✅ **Set appropriate image quality** - Balance size vs clarity
2. ✅ **Use background tasks** - For large PDFs
3. ✅ **Validate question quality** - Review generated questions
4. ✅ **Monitor database size** - Images increase storage needs
5. ✅ **Cache processed PDFs** - Avoid reprocessing
6. ✅ **Log extraction results** - Track success/failure rates

## Example Output

See `image_questions_output.json` after running the example script.

## Support

For issues or questions:

1. Check logs in `logs/` directory
2. Review error messages
3. Verify PDF quality and image clarity
4. Ensure all dependencies are installed
