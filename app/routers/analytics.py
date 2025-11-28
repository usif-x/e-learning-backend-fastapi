from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin, get_current_user
from app.schemas.analytics import PlatformAnalytics, UserAnalytics
from app.services.analytics import AnalyticsService

# from app.core.auth import get_current_active_superuser # Assuming we want to protect this

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
)


@router.get("/", response_model=PlatformAnalytics)
def get_platform_analytics(
    db: Session = Depends(get_db),
    # current_admin = Depends(get_current_admin), # Uncomment to protect
):
    """
    Get platform-wide analytics.
    """
    service = AnalyticsService(db)
    return service.get_platform_analytics()


@router.get("/user/me", response_model=UserAnalytics)
def get_user_analytics(
    db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    service = AnalyticsService(db)
    return service.get_user_analytics(current_user.id)


@router.get("/user/{user_id}", response_model=UserAnalytics)
def get_user_analytics_for_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """Admin-only endpoint: get analytics for a specific user by id."""
    service = AnalyticsService(db)
    return service.get_user_analytics(user_id)
