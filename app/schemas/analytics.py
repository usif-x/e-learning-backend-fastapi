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


class UserAnalytics(BaseModel):
    user_id: int
    total_courses_enrolled: int
    enrolled_quizzes_count: int
    attempted_quizzes_count: int
    quiz_attempts_ratio: float
    avg_course_quiz_score: float | None
    avg_user_generated_questions_score: float | None
    total_quiz_attempts: int
    total_quizzes_passed: int
    avg_time_per_quiz_attempt_seconds: float | None
    ugq_attempts_count: int
    ugq_avg_time_seconds: float | None
    total_user_generated_questions: int
    courses_completed_count: int
    course_completion_rate: float
    top_courses_by_score: list[dict] = []
