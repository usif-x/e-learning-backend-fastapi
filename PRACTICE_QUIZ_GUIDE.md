# Practice Quiz System - User Guide

## Overview

The Practice Quiz system allows users to review their incorrect and unanswered questions from past quiz attempts. It creates a practice quiz that works exactly like regular quizzes with all the same features.

## Features

- ✅ Generate quiz from incorrect/unanswered questions
- ✅ Filter by specific course (optional)
- ✅ Choose number of questions (1-50)
- ✅ Include/exclude unanswered questions
- ✅ All quiz features work: start, resume, submit, stats
- ✅ Unlimited attempts for practice
- ✅ Always shows correct answers after submission
- ✅ No time limit

## API Endpoints

### 1. Generate Practice Quiz

**POST** `/users/me/practice-quiz/generate`

Creates a practice quiz from user's past mistakes.

**Request Body:**

```json
{
  "course_id": 2, // Optional: filter by course
  "question_count": 10, // Number of questions (1-50)
  "include_unanswered": true // Include unanswered questions
}
```

**Response:**

```json
{
  "content": {
    "id": 123,              // Practice quiz content ID
    "course_id": 2,         // 0 if no specific course
    "lecture_id": 0,        // 0 for practice quizzes
    "content_type": "quiz",
    "questions": [...],     // Questions without correct answers
    "title": "Practice Quiz - Review Mistakes (Course 2)",
    "description": "Practice quiz generated from your incorrect and unanswered questions",
    "max_attempts": null,   // Unlimited
    "quiz_duration": null,  // No time limit
    "show_correct_answers": 1
  },
  "attempt_id": 456,        // Attempt ID to use when submitting
  "attempts_used": 0,
  "attempts_remaining": null,
  "can_attempt": true,
  "message": "Practice quiz generated with 10 questions"
}
```

### 2. Submit Practice Quiz

**POST** `/courses/{course_id}/lectures/{lecture_id}/contents/{content_id}/attempts`

Use the `content_id` and `attempt_id` from generate response.

**Note:** For practice quizzes, use `course_id=0` and `lecture_id=0`:

```
POST /courses/0/lectures/0/contents/123/attempts
```

**Request Body:**

```json
{
  "answers": [
    {"question_index": 0, "selected_answer": 1},
    {"question_index": 1, "selected_answer": 2},
    ...
  ],
  "time_taken": 120,
  "started_at": "2025-11-16T10:00:00Z",
  "attempt_id": 456
}
```

**Response:**

```json
{
  "id": 456,
  "score": 80.0,
  "total_questions": 10,
  "correct_answers": 8,
  "time_taken": 120,
  "questions_with_results": [
    {
      "question": "What is...",
      "options": ["A", "B", "C", "D"],
      "user_answer": 1,
      "correct_answer": 1,
      "is_correct": true,
      "explanation_en": "...",
      "explanation_ar": "..."
    },
    ...
  ]
}
```

### 3. Get Practice Quiz Attempts

**GET** `/courses/0/lectures/0/contents/{content_id}/attempts`

List all attempts for a practice quiz.

### 4. Get Practice Quiz Stats

**GET** `/courses/0/lectures/0/contents/{content_id}/stats`

Get statistics for practice quiz attempts.

### 5. Resume Practice Quiz

**GET** `/courses/0/lectures/0/contents/{content_id}/resume-quiz`

Resume an incomplete practice quiz attempt.

## Usage Flow

### Generate and Take Practice Quiz

```javascript
// 1. Generate practice quiz from mistakes
const generateResponse = await fetch("/users/me/practice-quiz/generate", {
  method: "POST",
  body: JSON.stringify({
    course_id: 2, // Optional: specific course
    question_count: 15,
    include_unanswered: true,
  }),
});

const { content, attempt_id } = await generateResponse.json();
const practiceQuizId = content.id;

// 2. User answers questions (store in localStorage)
localStorage.setItem(`quiz_attempt_${attempt_id}`, JSON.stringify(answers));

// 3. Submit practice quiz
const submitResponse = await fetch(
  `/courses/0/lectures/0/contents/${practiceQuizId}/attempts`,
  {
    method: "POST",
    body: JSON.stringify({
      answers: answers,
      time_taken: timeInSeconds,
      started_at: startTime,
      attempt_id: attempt_id,
    }),
  }
);

const results = await submitResponse.json();
// Results include correct answers and explanations
```

### Get All Mistakes from Specific Course

```javascript
const response = await fetch("/users/me/practice-quiz/generate", {
  method: "POST",
  body: JSON.stringify({
    course_id: 5, // Only questions from course 5
    question_count: 20,
    include_unanswered: true,
  }),
});
```

### Get All Mistakes (All Courses)

```javascript
const response = await fetch("/users/me/practice-quiz/generate", {
  method: "POST",
  body: JSON.stringify({
    course_id: null, // All courses
    question_count: 30,
    include_unanswered: true,
  }),
});
```

## Key Differences from Regular Quizzes

| Feature        | Regular Quiz              | Practice Quiz              |
| -------------- | ------------------------- | -------------------------- |
| Attempts       | Limited by `max_attempts` | Unlimited                  |
| Time Limit     | Can have `quiz_duration`  | No time limit              |
| Show Answers   | Based on quiz setting     | Always shows answers       |
| Course/Lecture | Real course/lecture IDs   | course_id=0, lecture_id=0  |
| Source         | Admin created             | Generated from mistakes    |
| Persistence    | Permanent                 | Can be regenerated anytime |

## Notes

- Practice quizzes use `course_id=0` and `lecture_id=0` as identifiers
- Questions are unique (no duplicates)
- Questions are collected from all past completed attempts
- Only incorrect or unanswered questions are included
- If no mistakes found, returns 404 error
- Practice quizzes can be attempted unlimited times
- Always shows correct answers and explanations after submission
