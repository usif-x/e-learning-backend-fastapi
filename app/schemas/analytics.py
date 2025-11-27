from pydantic import BaseModel

class PlatformAnalytics(BaseModel):
    total_users: int
    total_active_users: int
    total_courses: int
    total_enrollments: int
    total_lectures: int
    total_comments: int
    total_practice_quizzes: int
    total_quiz_attempts: int
    total_user_questions: int
