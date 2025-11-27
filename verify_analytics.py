import sys
import os

# Add the backend directory to the python path
sys.path.append("/Users/home/WorkSpace/WebApps/fullstack/e-learning/backend")

from app.core.database import SessionLocal
from app.services.analytics import AnalyticsService

def verify_analytics():
    db = SessionLocal()
    try:
        service = AnalyticsService(db)
        analytics = service.get_platform_analytics()
        print("Analytics Verification Successful:")
        print(f"Total Users: {analytics.total_users}")
        print(f"Total Active Users: {analytics.total_active_users}")
        print(f"Total Courses: {analytics.total_courses}")
        print(f"Total Enrollments: {analytics.total_enrollments}")
        print(f"Total Lectures: {analytics.total_lectures}")
        print(f"Total Comments: {analytics.total_comments}")
        print(f"Total Practice Quizzes: {analytics.total_practice_quizzes}")
        print(f"Total Quiz Attempts: {analytics.total_quiz_attempts}")
        print(f"Total User Questions: {analytics.total_user_questions}")
    except Exception as e:
        print(f"Verification Failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_analytics()
