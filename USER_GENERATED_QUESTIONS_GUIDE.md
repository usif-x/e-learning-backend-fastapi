# User Generated Questions System

## Overview

A comprehensive question generation and sharing system that allows users to:

- Generate quiz questions using AI from topics or PDF files
- Share questions publicly or keep them private
- Add more questions to existing sets (AI avoids duplicates)
- Attempt questions created by other users
- Track attempts and scores

## Features

### 1. Question Generation

#### Generate from Topic

```http
POST /user-questions/generate
```

**Request Body:**

```json
{
  "topic": "Python Programming Basics",
  "title": "My Python Quiz",
  "description": "Basic Python concepts",
  "difficulty": "medium",
  "question_type": "mixed",
  "count": 10,
  "is_public": true,
  "notes": "Focus on practical examples"
}
```

**Response:** Complete question set with all questions and metadata

#### Generate from PDF

```http
POST /user-questions/generate-from-pdf
Content-Type: multipart/form-data
```

**Form Data:**

- `file`: PDF file
- `title`: Question set title
- `description`: Optional description
- `difficulty`: easy/medium/hard
- `question_type`: multiple_choice/true_false/essay/mixed
- `count`: Number of questions (1-50)
- `is_public`: true/false
- `notes`: Optional AI instructions

### 2. Add More Questions

Add questions to existing sets - AI automatically avoids duplicates:

```http
POST /user-questions/{question_set_id}/add-questions
```

**Request Body:**

```json
{
  "count": 5,
  "notes": "Focus on advanced concepts this time"
}
```

**How Duplicate Prevention Works:**

- System extracts all existing question texts
- Sends them to AI with explicit "DO NOT REPEAT" instructions
- AI generates completely new questions with different angles

### 3. Manage Your Questions

#### List Your Question Sets

```http
GET /user-questions/my?page=1&size=20
```

#### Get Detailed View

```http
GET /user-questions/my/{question_set_id}
```

Shows all questions with correct answers (creator only)

#### Update Question Set

```http
PATCH /user-questions/my/{question_set_id}
```

**Request Body:**

```json
{
  "title": "Updated Title",
  "description": "New description",
  "is_public": false
}
```

#### Delete Question Set

```http
DELETE /user-questions/my/{question_set_id}
```

### 4. Public Questions (Discovery)

Browse and attempt public questions created by others:

```http
GET /user-questions/public?page=1&size=20&difficulty=medium&search=python
```

**Response includes:**

- Question set metadata
- Creator name
- Total attempts by all users
- Your attempt status (attempted or not)
- Your best score if attempted

### 5. Attempt Questions

#### Start Attempt

```http
POST /user-questions/{question_set_id}/attempt
```

**Response:**

```json
{
  "attempt_id": 123,
  "question_set_id": 45,
  "title": "Python Basics Quiz",
  "topic": "Python Programming",
  "difficulty": "medium",
  "total_questions": 10,
  "questions": [
    {
      "question": "What is a list in Python?",
      "options": ["A", "B", "C", "D"],
      "question_type": "multiple_choice"
    }
  ],
  "started_at": "2025-11-16T15:30:00Z"
}
```

**Note:** Questions are returned WITHOUT correct answers

#### Submit Attempt

```http
POST /user-questions/attempts/{attempt_id}/submit
```

**Request Body:**

```json
{
  "answers": [
    { "question_index": 0, "selected_answer": 2 },
    { "question_index": 1, "selected_answer": 0 }
  ],
  "time_taken": 180
}
```

**Response:** Detailed results with correct answers and explanations

### 6. View Attempts

#### List All Your Attempts

```http
GET /user-questions/attempts/my?page=1&size=20
```

#### Get Attempt Details

```http
GET /user-questions/attempts/{attempt_id}
```

Shows complete results with questions, your answers, correct answers, and explanations

## Database Schema

### user_generated_questions

- `id`: Primary key
- `user_id`: Creator (FK to users)
- `title`: Question set title
- `description`: Optional description
- `topic`: Main topic
- `difficulty`: easy/medium/hard
- `question_type`: multiple_choice/true_false/essay/mixed
- `is_public`: Privacy setting
- `questions`: JSONB array of questions
- `total_questions`: Count
- `source_type`: 'topic' or 'pdf'
- `source_file_name`: PDF filename if applicable
- `attempt_count`: Total attempts by all users
- `created_at`, `updated_at`: Timestamps

### user_generated_question_attempts

- `id`: Primary key
- `question_set_id`: FK to user_generated_questions
- `user_id`: Attempt user (FK to users)
- `answers`: JSONB array of user answers
- `score`: Percentage score
- `correct_answers`: Count of correct answers
- `total_questions`: Total questions attempted
- `time_taken`: Seconds
- `is_completed`: Completion status
- `started_at`, `completed_at`: Timestamps

## Question Format

Questions are stored as JSONB with this structure:

```json
{
  "question": "What is Python?",
  "options": ["A programming language", "A snake", "A tool", "None"],
  "correct_answer": 0,
  "explanation_en": "Python is a high-level programming language...",
  "explanation_ar": "بايثون هي لغة برمجة عالية المستوى...",
  "question_type": "multiple_choice"
}
```

## Privacy System

- **Private Questions** (`is_public: false`):

  - Only creator can view and attempt
  - Not shown in public listings
  - Perfect for personal practice

- **Public Questions** (`is_public: true`):
  - Visible in public listings
  - Anyone can attempt
  - Creator name shown
  - Attempt statistics visible to all

## AI Integration

### Duplicate Prevention

When adding more questions:

1. System extracts all existing question texts
2. Sends to AI: `previous_questions: ["Question 1", "Question 2", ...]`
3. AI receives explicit instructions to avoid duplicates
4. AI generates completely new questions using different:
   - Angles and perspectives
   - Examples and contexts
   - Concepts and details

### Question Quality

- Uses DeepSeek AI with temperature 0.9 for diversity
- Supports bilingual explanations (English + Arabic)
- Multiple question types in one set
- Intelligent topic-based generation
- PDF content extraction and analysis

## Use Cases

1. **Personal Study**

   - Generate questions on topics you're learning
   - Keep private for personal practice
   - Add more questions as you progress

2. **Teaching**

   - Create question banks from course materials
   - Share publicly with students
   - Generate from lecture PDFs

3. **Peer Learning**

   - Create and share questions with classmates
   - Attempt each other's questions
   - Compare scores and learn together

4. **Exam Preparation**
   - Generate practice questions on exam topics
   - Mix different difficulty levels
   - Track your progress over multiple attempts

## API Endpoints Summary

| Method | Endpoint                               | Description                | Auth     |
| ------ | -------------------------------------- | -------------------------- | -------- |
| POST   | `/user-questions/generate`             | Generate from topic        | Required |
| POST   | `/user-questions/generate-from-pdf`    | Generate from PDF          | Required |
| POST   | `/user-questions/{id}/add-questions`   | Add more questions         | Required |
| GET    | `/user-questions/my`                   | List my question sets      | Required |
| GET    | `/user-questions/my/{id}`              | Get my question set detail | Required |
| PATCH  | `/user-questions/my/{id}`              | Update question set        | Required |
| DELETE | `/user-questions/my/{id}`              | Delete question set        | Required |
| GET    | `/user-questions/public`               | Browse public questions    | Required |
| POST   | `/user-questions/{id}/attempt`         | Start attempt              | Required |
| POST   | `/user-questions/attempts/{id}/submit` | Submit attempt             | Required |
| GET    | `/user-questions/attempts/my`          | List my attempts           | Required |
| GET    | `/user-questions/attempts/{id}`        | Get attempt detail         | Required |

## Migration

Run the migration to create tables:

```bash
alembic upgrade head
```

Or manually:

```bash
cd /Users/home/WorkSpace/WebApps/fullstack/e-learning/backend
alembic upgrade head
```

## Testing

### Generate Questions

```bash
curl -X POST http://localhost:8000/user-questions/generate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Python Basics",
    "title": "My First Quiz",
    "difficulty": "easy",
    "count": 5,
    "is_public": true
  }'
```

### Browse Public Questions

```bash
curl -X GET "http://localhost:8000/user-questions/public?page=1&size=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Attempt Questions

```bash
curl -X POST http://localhost:8000/user-questions/45/attempt \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Best Practices

1. **Descriptive Titles**: Use clear titles that describe the content
2. **Privacy Settings**: Make educational content public, personal practice private
3. **Add Gradually**: Start with 5-10 questions, add more as needed
4. **Use Notes**: Provide specific instructions to AI for better questions
5. **Mix Types**: Use 'mixed' question type for variety
6. **Track Progress**: Review your attempts to identify weak areas

## Future Enhancements

- [ ] Question difficulty ratings based on attempt success rates
- [ ] Leaderboards for public question sets
- [ ] Comments and discussions on question sets
- [ ] Question set collections/folders
- [ ] Export to PDF or other formats
- [ ] Collaborative question editing
- [ ] Question tagging system
- [ ] Analytics dashboard for creators
