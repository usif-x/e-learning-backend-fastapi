from sqlalchemy.orm import Session
from app.models.user import User
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.lecture import Lecture
from app.models.comment import Comment
from app.models.practice_quiz import PracticeQuiz
from app.models.quiz_attempt import QuizAttempt
from app.models.user_generated_question import UserGeneratedQuestion
from app.models.community import Community
from app.models.post import Post
from app.schemas.analytics import PlatformAnalytics

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_platform_analytics(self) -> PlatformAnalytics:
        """
        Get overall platform analytics.
        """
        total_users = self.db.query(User).count()
        total_active_users = self.db.query(User).filter(User.is_active == True).count()
        total_courses = self.db.query(Course).count()
        total_enrollments = self.db.query(CourseEnrollment).count()
        total_lectures = self.db.query(Lecture).count()
        total_comments = self.db.query(Comment).count()
        total_practice_quizzes = self.db.query(PracticeQuiz).count()
        total_quiz_attempts = self.db.query(QuizAttempt).count()
        total_user_questions = self.db.query(UserGeneratedQuestion).count()
        total_communities = self.db.query(Community).count()
        total_posts = self.db.query(Post).count()
        return PlatformAnalytics(
            total_users=total_users,
            total_active_users=total_active_users,
            total_courses=total_courses,
            total_enrollments=total_enrollments,
            total_lectures=total_lectures,
            total_communities=total_communities,
            total_posts=total_posts,
            total_comments=total_comments,
            total_practice_quizzes=total_practice_quizzes,
            total_quiz_attempts=total_quiz_attempts,
            total_user_questions=total_user_questions,
        )
