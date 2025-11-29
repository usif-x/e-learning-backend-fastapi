from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.user_daily_usage import (
    UsageChartResponse,
    UsageMonthResponse,
    UsagePingResponse,
    UsageRangeResponse,
    UsageStartResponse,
    UsageTodayResponse,
    UsageWeekResponse,
)
from app.services.user_daily_usage import UsageService

router = APIRouter(prefix="/usage", tags=["usage"])


@router.post("/start", response_model=UsageStartResponse)
def start_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # <--- UPDATED
):
    """Start a new activity session."""
    # We use current_user.id to get the ID from the token
    usage = UsageService.start_session(db, current_user.id)

    return UsageStartResponse(
        user_id=usage.user_id,
        date=usage.date,
        message="Session started successfully",
        last_ping=usage.last_ping,
    )


@router.post("/ping", response_model=UsagePingResponse)
def ping_activity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # <--- UPDATED
):
    """Ping user activity."""
    usage, minutes_added = UsageService.ping_activity(db, current_user.id)

    return UsagePingResponse(
        user_id=usage.user_id,
        date=usage.date,
        minutes_added=minutes_added,
        total_minutes_today=usage.minutes_spent,
        last_ping=usage.last_ping,
    )


@router.get("/today", response_model=UsageTodayResponse)
def get_today_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # <--- UPDATED
):
    """Get total minutes spent today."""
    total_minutes = UsageService.get_today_usage(db, current_user.id)

    return UsageTodayResponse(
        user_id=current_user.id, date=date.today(), total_minutes=total_minutes
    )


@router.get("/week", response_model=UsageWeekResponse)
def get_week_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # <--- UPDATED
):
    """Get total minutes spent this week."""
    total_minutes, week_start, week_end = UsageService.get_week_usage(
        db, current_user.id
    )

    return UsageWeekResponse(
        user_id=current_user.id,
        week_start=week_start,
        week_end=week_end,
        total_minutes=total_minutes,
    )


@router.get("/month", response_model=UsageMonthResponse)
def get_month_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # <--- UPDATED
):
    """Get total minutes spent this month."""
    total_minutes = UsageService.get_month_usage(db, current_user.id)
    today = date.today()

    return UsageMonthResponse(
        user_id=current_user.id,
        month=today.month,
        year=today.year,
        total_minutes=total_minutes,
    )


@router.get("/range", response_model=UsageRangeResponse)
def get_range_usage(
    start: Annotated[date, Query(description="Start date (YYYY-MM-DD)")],
    end: Annotated[date, Query(description="End date (YYYY-MM-DD)")],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # <--- UPDATED
):
    """Get total minutes spent in a custom date range."""
    if start > end:
        raise HTTPException(
            status_code=400, detail="Start date must be before or equal to end date"
        )

    total_minutes = UsageService.get_range_usage(db, current_user.id, start, end)

    return UsageRangeResponse(
        user_id=current_user.id,
        start_date=start,
        end_date=end,
        total_minutes=total_minutes,
    )


@router.get("/chart/week", response_model=UsageChartResponse)
def get_week_chart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # <--- UPDATED
):
    """Get daily breakdown for the current week for charts."""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    result = UsageService.get_chart_data(db, current_user.id, week_start, week_end)

    return UsageChartResponse(
        user_id=current_user.id,
        start_date=week_start,
        end_date=week_end,
        total_minutes_period=result["total_minutes"],
        data=result["data"],
    )


@router.get("/chart/month", response_model=UsageChartResponse)
def get_month_chart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # <--- UPDATED
):
    """Get daily breakdown for the current month for charts."""
    today = date.today()
    import calendar

    _, last_day = calendar.monthrange(today.year, today.month)

    month_start = date(today.year, today.month, 1)
    month_end = date(today.year, today.month, last_day)

    result = UsageService.get_chart_data(db, current_user.id, month_start, month_end)

    return UsageChartResponse(
        user_id=current_user.id,
        start_date=month_start,
        end_date=month_end,
        total_minutes_period=result["total_minutes"],
        data=result["data"],
    )


@router.get("/chart/range", response_model=UsageChartResponse)
def get_custom_range_chart(
    start: Annotated[date, Query(description="Start date")],
    end: Annotated[date, Query(description="End date")],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # <--- UPDATED
):
    """Get daily breakdown for a custom range for charts."""
    if start > end:
        raise HTTPException(
            status_code=400, detail="Start date must be before end date"
        )

    if (end - start).days > 366:
        raise HTTPException(status_code=400, detail="Date range cannot exceed 1 year")

    result = UsageService.get_chart_data(db, current_user.id, start, end)

    return UsageChartResponse(
        user_id=current_user.id,
        start_date=start,
        end_date=end,
        total_minutes_period=result["total_minutes"],
        data=result["data"],
    )
