from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class UsageStartResponse(BaseModel):
    """Response when starting a new session"""

    user_id: int
    date: date
    message: str
    last_ping: datetime


class UsagePingResponse(BaseModel):
    """Response when pinging activity"""

    user_id: int
    date: date
    minutes_added: int
    total_minutes_today: int
    last_ping: datetime


class UsageTodayResponse(BaseModel):
    """Today's usage summary"""

    user_id: int
    date: date
    total_minutes: int


class UsageWeekResponse(BaseModel):
    """Weekly usage summary"""

    user_id: int
    week_start: date
    week_end: date
    total_minutes: int


class UsageMonthResponse(BaseModel):
    """Monthly usage summary"""

    user_id: int
    month: int
    year: int
    total_minutes: int


class UsageRangeResponse(BaseModel):
    """Custom date range usage summary"""

    user_id: int
    start_date: date
    end_date: date
    total_minutes: int


class DailyUsagePoint(BaseModel):
    date: date
    minutes: int

    class Config:
        from_attributes = True


# New Response model for Chart Data
class UsageChartResponse(BaseModel):
    user_id: int
    start_date: date
    end_date: date
    total_minutes_period: int
    data: List[DailyUsagePoint]  # This is the array for your chart


class ErrorResponse(BaseModel):
    """Error response"""

    detail: str
