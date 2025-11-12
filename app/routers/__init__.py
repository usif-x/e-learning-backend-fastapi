from .admin import router as admin_router
from .auth import router as auth_router
from .categories import router as category_router
from .course_prepaidable_users import router as course_prepaidable_users_router
from .course_subscription import router as course_subscription_router
from .courses import router as course_router
from .user import router as user_router

routes = [
    admin_router,
    auth_router,
    course_router,
    category_router,
    user_router,
    course_subscription_router,
    course_prepaidable_users_router,
]
