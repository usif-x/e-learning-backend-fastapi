from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
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


# Mock dependency for current user
# Replace this with your actual authentication dependency
def get_current_user_id() -> int:
    """Mock current user - replace with actual auth"""
    # In production, this would extract user_id from JWT token or session
    return 1  # Mock user ID


@router.post("/start", response_model=UsageStartResponse)
def start_session(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    """
    Start a new activity session.
    Records the current timestamp as the session start time.
    """
    usage = UsageService.start_session(db, user_id)

    return UsageStartResponse(
        user_id=usage.user_id,
        date=usage.date,
        message="Session started successfully",
        last_ping=usage.last_ping,
    )


@router.post("/ping", response_model=UsagePingResponse)
def ping_activity(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    """
    Ping user activity.
    Calculates minutes since last ping and updates the database.
    Should be called periodically (e.g., every 1-5 minutes) while user is active.
    """
    usage, minutes_added = UsageService.ping_activity(db, user_id)

    return UsagePingResponse(
        user_id=usage.user_id,
        date=usage.date,
        minutes_added=minutes_added,
        total_minutes_today=usage.minutes_spent,
        last_ping=usage.last_ping,
    )


@router.get("/today", response_model=UsageTodayResponse)
def get_today_usage(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    """
    Get total minutes spent today.
    """
    total_minutes = UsageService.get_today_usage(db, user_id)

    return UsageTodayResponse(
        user_id=user_id, date=date.today(), total_minutes=total_minutes
    )


@router.get("/week", response_model=UsageWeekResponse)
def get_week_usage(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    """
    Get total minutes spent this week (Monday to Sunday).
    """
    total_minutes, week_start, week_end = UsageService.get_week_usage(db, user_id)

    return UsageWeekResponse(
        user_id=user_id,
        week_start=week_start,
        week_end=week_end,
        total_minutes=total_minutes,
    )


@router.get("/month", response_model=UsageMonthResponse)
def get_month_usage(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    """
    Get total minutes spent this month.
    """
    total_minutes = UsageService.get_month_usage(db, user_id)
    today = date.today()

    return UsageMonthResponse(
        user_id=user_id, month=today.month, year=today.year, total_minutes=total_minutes
    )


@router.get("/range", response_model=UsageRangeResponse)
def get_range_usage(
    start: Annotated[date, Query(description="Start date (YYYY-MM-DD)")],
    end: Annotated[date, Query(description="End date (YYYY-MM-DD)")],
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Get total minutes spent in a custom date range.
    Both start and end dates are inclusive.
    """
    if start > end:
        raise HTTPException(
            status_code=400, detail="Start date must be before or equal to end date"
        )

    total_minutes = UsageService.get_range_usage(db, user_id, start, end)

    return UsageRangeResponse(
        user_id=user_id, start_date=start, end_date=end, total_minutes=total_minutes
    )


@router.get("/chart/week", response_model=UsageChartResponse)
def get_week_chart(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    """
    Get daily breakdown for the current week (Mon-Sun) for charts.
    """
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_end = week_start + timedelta(days=6)  # Sunday

    result = UsageService.get_chart_data(db, user_id, week_start, week_end)

    return UsageChartResponse(
        user_id=user_id,
        start_date=week_start,
        end_date=week_end,
        total_minutes_period=result["total_minutes"],
        data=result["data"],
    )


@router.get("/chart/month", response_model=UsageChartResponse)
def get_month_chart(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    """
    Get daily breakdown for the current month for charts.
    """
    today = date.today()

    # Calculate first and last day of current month
    import calendar

    _, last_day = calendar.monthrange(today.year, today.month)

    month_start = date(today.year, today.month, 1)
    month_end = date(today.year, today.month, last_day)

    result = UsageService.get_chart_data(db, user_id, month_start, month_end)

    return UsageChartResponse(
        user_id=user_id,
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
    user_id: int = Depends(get_current_user_id),
):
    """
    Get daily breakdown for a custom range for charts.
    """
    if start > end:
        raise HTTPException(
            status_code=400, detail="Start date must be before end date"
        )

    # Optional: Limit range to prevent massive queries (e.g., max 1 year)
    if (end - start).days > 366:
        raise HTTPException(status_code=400, detail="Date range cannot exceed 1 year")

    result = UsageService.get_chart_data(db, user_id, start, end)

    return UsageChartResponse(
        user_id=user_id,
        start_date=start,
        end_date=end,
        total_minutes_period=result["total_minutes"],
        data=result["data"],
    )
