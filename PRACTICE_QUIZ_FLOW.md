# Practice Quiz - Complete Flow

## Step 1: Generate Practice Quiz

**POST** `/users/me/practice-quiz/generate`

```json
{
  "course_id": 2, // Optional: filter by course
  "question_count": 10,
  "include_unanswered": true
}
```

**Response:**

```json
{
  "content": {
    "id": 123,              // Content ID (use this for submit)
    "course_id": 2,
    "lecture_id": 5,
    "questions": [...],     // Questions without correct answers
    "title": "Practice Quiz - Review Mistakes (Course 2)"
  },
  "attempt_id": 456,        // Use this when submitting
  "attempts_used": 0,
  "can_attempt": true
}
```

## Step 2: Submit Practice Quiz

**POST** `/users/me/practice-quiz/{attempt_id}/submit`

Use the `attempt_id` from Step 1 response. This is a dedicated endpoint for practice quizzes only - NOT related to any course/lecture content.

Example: `POST /users/me/practice-quiz/456/submit`

```json
{
  "answers": [
    {"question_index": 0, "selected_answer": 1},
    {"question_index": 1, "selected_answer": 2},
    {"question_index": 2, "selected_answer": null},  // Unanswered
    ...
  ],
  "time_taken": 120,
  "started_at": "2025-11-16T10:00:00Z"
}
```

**Response (Shows Results with Correct Answers):**

```json
{
  "id": 456,
  "score": 80.0,
  "total_questions": 10,
  "correct_answers": 8,
  "time_taken": 120,
  "is_completed": 1,
  "questions_with_results": [
    {
      "question": "Which organ system regulates blood glucose?",
      "options": ["Nervous", "Endocrine", "Digestive", "Respiratory"],
      "user_answer": 1,
      "correct_answer": 1,
      "is_correct": true,
      "explanation_en": "The endocrine system...",
      "explanation_ar": "نظام الغدد الصماء..."
    },
    {
      "question": "What is homeostasis?",
      "options": ["...", "...", "...", "..."],
      "user_answer": 2,
      "correct_answer": 0,
      "is_correct": false,
      "explanation_en": "Homeostasis is...",
      "explanation_ar": "الاستتباب هو..."
    }
    // ... more questions
  ]
}
```

## Step 3: View Practice Quiz Attempts (Optional)

**GET** `/users/me/quiz-analytics?course_id=2`

Shows all quiz attempts including practice quizzes (filtered by title "Practice Quiz").

**Response:**

```json
{
  "quizzes": [
    {
      "content_id": 123,
      "quiz_title": "Practice Quiz - Review Mistakes (Course 2)",
      "attempt_id": 456,
      "score": 80.0,
      "correct_answers": 8,
      "total_questions": 10
    }
  ],
  "total": 1
}
```

## Step 4: View Specific Attempt Details

**GET** `/users/me/quiz-analytics/{attempt_id}`

Example: `GET /users/me/quiz-analytics/456`

**Response (Shows Wrong Answers with Explanations):**

```json
{
  "content_id": 123,
  "quiz_title": "Practice Quiz - Review Mistakes (Course 2)",
  "attempt_id": 456,
  "score": 80.0,
  "correct_answers": 8,
  "total_questions": 10,
  "questions_with_results": [
    {
      "question": "What is homeostasis?",
      "options": [
        "Maintaining stable conditions",
        "Growth",
        "Reproduction",
        "Energy use"
      ],
      "user_answer": 2,
      "correct_answer": 0,
      "is_correct": false,
      "explanation_en": "Homeostasis is the ability to maintain stable internal conditions...",
      "explanation_ar": "الاستتباب هو القدرة على الحفاظ على الظروف الداخلية المستقرة..."
    }
    // ... all questions with results
  ]
}
```

## Complete JavaScript Example

```javascript
// 1. Generate practice quiz
async function generatePracticeQuiz(courseId = null, count = 10) {
  const response = await fetch("/users/me/practice-quiz/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      course_id: courseId,
      question_count: count,
      include_unanswered: true,
    }),
  });

  const data = await response.json();
  return {
    contentId: data.content.id,
    courseId: data.content.course_id,
    lectureId: data.content.lecture_id,
    attemptId: data.attempt_id,
    questions: data.content.questions,
  };
}

// 2. Submit practice quiz
async function submitPracticeQuiz(attemptId, answers, startTime) {
  const timeInSeconds = Math.floor((Date.now() - startTime) / 1000);

  const response = await fetch(`/users/me/practice-quiz/${attemptId}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      answers: answers,
      time_taken: timeInSeconds,
      started_at: new Date(startTime).toISOString(),
    }),
  });

  const result = await response.json();
  return result; // Contains score, correct answers, and detailed results
}

// 3. View wrong answers
async function viewWrongAnswers(attemptId) {
  const response = await fetch(`/users/me/quiz-analytics/${attemptId}`);
  const data = await response.json();

  // Filter only incorrect answers
  const wrongAnswers = data.questions_with_results.filter((q) => !q.is_correct);
  return wrongAnswers;
}

// Complete Flow Example
async function practiceQuizFlow() {
  // Generate practice quiz from course 2 mistakes
  const quiz = await generatePracticeQuiz(2, 15);
  console.log("Practice quiz generated:", quiz.questions);

  // User answers questions
  const answers = [
    { question_index: 0, selected_answer: 1 },
    { question_index: 1, selected_answer: 2 },
    // ... user's answers
  ];

  const startTime = Date.now();

  // Submit quiz
  const result = await submitPracticeQuiz(quiz.attemptId, answers, startTime);

  console.log("Score:", result.score);
  console.log("Correct:", result.correct_answers, "/", result.total_questions);

  // Show results with explanations
  result.questions_with_results.forEach((q) => {
    if (!q.is_correct) {
      console.log("Wrong:", q.question);
      console.log("You answered:", q.options[q.user_answer]);
      console.log("Correct answer:", q.options[q.correct_answer]);
      console.log("Explanation:", q.explanation_en);
    }
  });
}
```

## Key Points

1. **Generate** creates a practice quiz and returns `attempt_id` needed for submission
2. **Submit** using dedicated practice quiz endpoint: `/users/me/practice-quiz/{attempt_id}/submit`
3. **Results** automatically include correct answers and explanations (always shown for practice quizzes)
4. **Analytics** endpoints show detailed breakdown of all attempts including wrong answers
5. Practice quizzes are **user-specific** and **NOT tied to course/lecture content endpoints**
6. Practice quizzes have:
   - No time limit
   - Unlimited attempts
   - Always shows correct answers after submission

## Finding Wrong Answers

After submission, the response includes `questions_with_results` array where each question has:

- `is_correct: false` for wrong answers
- `user_answer` - what the user selected
- `correct_answer` - the right answer
- `explanation_en` and `explanation_ar` - explanations

Filter by `is_correct === false` to show only mistakes!
