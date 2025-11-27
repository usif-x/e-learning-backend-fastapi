from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.analytics import PlatformAnalytics
from app.services.analytics import AnalyticsService
from app.core.dependencies import get_current_admin
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
