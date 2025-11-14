from .admin import router as admin_router
from .auth import router as auth_router
from .community import router as community_router
from .user import router as user_router

routes = [
    admin_router,
    auth_router,
    user_router,
    community_router,
]
