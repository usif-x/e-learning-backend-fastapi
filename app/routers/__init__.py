from .admin import router as admin_router
from .ai import router as ai_router
from .auth import router as auth_router
from .category import router as category_router
from .community import router as community_router
from .course import router as course_router
from .lecture import router as lecture_router
from .user import router as user_router
from .user_generated_question import router as user_generated_question_router

routes = [
    admin_router,
    auth_router,
    user_router,
    category_router,
    course_router,
    lecture_router,
    community_router,
    ai_router,
    user_generated_question_router,
]
