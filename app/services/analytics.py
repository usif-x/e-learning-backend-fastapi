from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.community import Community
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.lecture import Lecture
from app.models.lecture_content import LectureContent
from app.models.post import Post
from app.models.practice_quiz import PracticeQuiz
from app.models.quiz_attempt import QuizAttempt
from app.models.user import User
from app.models.user_generated_question import (
    UserGeneratedQuestion,
    UserGeneratedQuestionAttempt,
)
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

    def get_user_analytics(self, user_id: int) -> dict:
        """
        Compute user-specific analytics:
        - total_courses_enrolled
        - enrolled_quizzes_count
        - attempted_quizzes_count
        - quiz_attempts_ratio = attempted_quizzes_count / enrolled_quizzes_count
        - avg_course_quiz_score: average of QuizAttempt.score across completed attempts in courses enrolled
        - avg_user_generated_questions_score: average score for UserGeneratedQuestionAttempt for the user
        """
        # Total courses enrolled
        total_courses_enrolled = (
            self.db.query(CourseEnrollment)
            .filter(CourseEnrollment.user_id == user_id)
            .count()
        )

        enrolled_course_ids = [
            r.course_id
            for r in (
                self.db.query(CourseEnrollment.course_id)
                .filter(CourseEnrollment.user_id == user_id)
                .all()
            )
        ]

        if enrolled_course_ids:
            # Count quizzes in enrolled courses
            enrolled_quizzes_count = (
                self.db.query(LectureContent)
                .filter(
                    LectureContent.course_id.in_(enrolled_course_ids),
                    LectureContent.content_type == "quiz",
                )
                .count()
            )

            # Count distinct attempted quizzes by user in those courses
            attempted_quizzes_count = (
                self.db.query(QuizAttempt)
                .filter(
                    QuizAttempt.user_id == user_id,
                    QuizAttempt.is_completed == 1,
                    QuizAttempt.course_id.in_(enrolled_course_ids),
                )
                .distinct(QuizAttempt.content_id)
                .count()
            )

            avg_course_quiz_score = (
                float(
                    self.db.query(func.avg(QuizAttempt.score))
                    .filter(
                        QuizAttempt.user_id == user_id,
                        QuizAttempt.is_completed == 1,
                        QuizAttempt.course_id.in_(enrolled_course_ids),
                    )
                    .scalar()
                    or 0
                )
                if self.db.query(QuizAttempt)
                .filter(
                    QuizAttempt.user_id == user_id,
                    QuizAttempt.is_completed == 1,
                    QuizAttempt.course_id.in_(enrolled_course_ids),
                )
                .count()
                else 0.0
            )
        else:
            enrolled_quizzes_count = 0
            attempted_quizzes_count = 0
            avg_course_quiz_score = 0.0

        # user generated questions avg
        avg_ugq_score = (
            float(
                self.db.query(func.avg(UserGeneratedQuestionAttempt.score))
                .filter(UserGeneratedQuestionAttempt.user_id == user_id)
                .scalar()
                or 0
            )
            if self.db.query(UserGeneratedQuestionAttempt)
            .filter(UserGeneratedQuestionAttempt.user_id == user_id)
            .count()
            else 0.0
        )

        ratio = round(
            (
                (attempted_quizzes_count / enrolled_quizzes_count)
                if enrolled_quizzes_count
                else 0
            ),
            4,
        )

        # total quiz attempts (completed)
        total_quiz_attempts = (
            self.db.query(QuizAttempt)
            .filter(QuizAttempt.user_id == user_id, QuizAttempt.is_completed == 1)
            .count()
        )

        # total quizzes passed (using course passing threshold if present)
        passed_q_count = 0
        if total_quiz_attempts:
            passed_q_count = (
                self.db.query(QuizAttempt)
                .join(LectureContent, QuizAttempt.content_id == LectureContent.id)
                .filter(
                    QuizAttempt.user_id == user_id,
                    QuizAttempt.is_completed == 1,
                    QuizAttempt.score
                    >= func.coalesce(LectureContent.passing_score, 50),
                )
                .count()
            )

        # average time per quiz attempt (seconds)
        avg_time_per_quiz_attempt_seconds = None
        if total_quiz_attempts:
            avg_time_per_quiz_attempt_seconds = float(
                self.db.query(func.avg(QuizAttempt.time_taken))
                .filter(QuizAttempt.user_id == user_id, QuizAttempt.is_completed == 1)
                .scalar()
                or 0
            )

        # UGQ attempts and stats
        ugq_attempts_count = (
            self.db.query(UserGeneratedQuestionAttempt)
            .filter(UserGeneratedQuestionAttempt.user_id == user_id)
            .count()
        )
        ugq_avg_time_seconds = None
        if ugq_attempts_count:
            ugq_avg_time_seconds = float(
                self.db.query(func.avg(UserGeneratedQuestionAttempt.time_taken))
                .filter(UserGeneratedQuestionAttempt.user_id == user_id)
                .scalar()
                or 0
            )

        total_user_generated_questions = (
            self.db.query(UserGeneratedQuestion)
            .filter(UserGeneratedQuestion.user_id == user_id)
            .count()
        )

        # Course completion
        courses_completed_count = (
            self.db.query(CourseEnrollment)
            .filter(
                CourseEnrollment.user_id == user_id,
                CourseEnrollment.completed_at != None,
            )
            .count()
        )
        course_completion_rate = (
            round((courses_completed_count / total_courses_enrolled), 4)
            if total_courses_enrolled
            else 0
        )

        # Top courses by avg score (for courses enrolled)
        top_courses = []
        if enrolled_course_ids:
            top_rows = (
                self.db.query(
                    QuizAttempt.course_id,
                    func.count(QuizAttempt.id).label("attempts_count"),
                    func.avg(QuizAttempt.score).label("avg_score"),
                    Course.name,
                )
                .join(Course, QuizAttempt.course_id == Course.id)
                .filter(
                    QuizAttempt.user_id == user_id,
                    QuizAttempt.is_completed == 1,
                    QuizAttempt.course_id.in_(enrolled_course_ids),
                )
                .group_by(QuizAttempt.course_id, Course.name)
                .order_by(func.avg(QuizAttempt.score).desc())
                .limit(3)
                .all()
            )
            for r in top_rows:
                top_courses.append(
                    {
                        "course_id": r.course_id,
                        "course_name": r.name,
                        "avg_score": (
                            float(r.avg_score) if r.avg_score is not None else 0.0
                        ),
                        "attempts_count": int(r.attempts_count),
                    }
                )

        return {
            "user_id": user_id,
            "total_courses_enrolled": total_courses_enrolled,
            "enrolled_quizzes_count": enrolled_quizzes_count,
            "attempted_quizzes_count": attempted_quizzes_count,
            "quiz_attempts_ratio": ratio,
            "avg_course_quiz_score": avg_course_quiz_score,
            "avg_user_generated_questions_score": avg_ugq_score,
            "total_quiz_attempts": total_quiz_attempts,
            "total_quizzes_passed": passed_q_count,
            "avg_time_per_quiz_attempt_seconds": avg_time_per_quiz_attempt_seconds,
            "ugq_attempts_count": ugq_attempts_count,
            "ugq_avg_time_seconds": ugq_avg_time_seconds,
            "total_user_generated_questions": total_user_generated_questions,
            "courses_completed_count": courses_completed_count,
            "course_completion_rate": course_completion_rate,
            "top_courses_by_score": top_courses,
        }
