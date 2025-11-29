from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, extract, func
from sqlalchemy.orm import Session

from app.models.user_daily_usage import UserDailyUsage


def make_aware(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware (UTC)"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def get_utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime"""
    return datetime.now(timezone.utc)


class UsageService:
    """Service layer for user activity tracking"""

    @staticmethod
    def start_session(db: Session, user_id: int) -> UserDailyUsage:
        """
        Start a new activity session for the user.
        Creates or updates today's usage record with current timestamp.
        """
        today = date.today()
        now = get_utc_now()

        # Check if record exists for today
        usage = (
            db.query(UserDailyUsage)
            .filter(
                and_(UserDailyUsage.user_id == user_id, UserDailyUsage.date == today)
            )
            .first()
        )

        if usage:
            # Update existing record
            usage.last_ping = now
            usage.updated_at = now
        else:
            # Create new record
            usage = UserDailyUsage(
                user_id=user_id, date=today, minutes_spent=0, last_ping=now
            )
            db.add(usage)

        db.commit()
        db.refresh(usage)
        return usage

    @staticmethod
    def ping_activity(db: Session, user_id: int) -> tuple[UserDailyUsage, int]:
        """
        Update user activity with multi-tab deduplication.
        Frontend sends pings every 70 seconds.
        Ignores pings that come within 35 seconds of the last ping (handles multi-tab).
        """
        today = date.today()
        now = get_utc_now()

        # Threshold to detect if user closed the browser/tab
        MAX_IDLE_MINUTES = 5

        # Deduplication window: ignore pings closer than 60 seconds
        # Frontend sends every 70s, so any ping < 60s apart is from another tab
        MIN_PING_INTERVAL_SECONDS = 60

        usage = (
            db.query(UserDailyUsage)
            .filter(
                and_(UserDailyUsage.user_id == user_id, UserDailyUsage.date == today)
            )
            .first()
        )

        minutes_added = 0

        if usage and usage.last_ping:
            # Ensure datetime is timezone-aware
            last_ping_aware = make_aware(usage.last_ping)

            # Calculate difference
            time_diff = now - last_ping_aware
            diff_seconds = time_diff.total_seconds()
            diff_minutes = diff_seconds / 60

            # DEDUPLICATION: Ignore if ping came too soon (likely from another tab)
            if diff_seconds < MIN_PING_INTERVAL_SECONDS:
                # Don't update anything, just return current state
                db.commit()
                return usage, 0

            if diff_minutes > MAX_IDLE_MINUTES:
                # Gap was too long (e.g., 3 hours).
                # User likely closed the site and came back.
                # Do NOT add these minutes. Just reset the timer.
                minutes_added = 0
            else:
                # User is active. Add the time.
                minutes_added = int(diff_minutes)
                # Cap at 5 minutes just in case of weird edge cases
                minutes_added = min(minutes_added, 5)

            # Update record
            usage.minutes_spent += minutes_added
            usage.last_ping = now
            usage.updated_at = now

        elif usage:
            # Record exists but no last_ping (shouldn't happen often)
            usage.last_ping = now
            usage.updated_at = now
        else:
            # No record exists for today - create one
            usage = UserDailyUsage(
                user_id=user_id, date=today, minutes_spent=0, last_ping=now
            )
            db.add(usage)

        db.commit()
        db.refresh(usage)
        return usage, minutes_added

    @staticmethod
    def get_today_usage(db: Session, user_id: int) -> int:
        """Get total minutes spent today"""
        today = date.today()

        usage = (
            db.query(UserDailyUsage)
            .filter(
                and_(UserDailyUsage.user_id == user_id, UserDailyUsage.date == today)
            )
            .first()
        )

        return usage.minutes_spent if usage else 0

    @staticmethod
    def get_week_usage(db: Session, user_id: int) -> tuple[int, date, date]:
        """
        Get total minutes spent this week (Monday to Sunday).
        Returns (total_minutes, week_start, week_end)
        """
        today = date.today()

        # Calculate start of week (Monday)
        week_start = today - timedelta(days=today.weekday())

        # Calculate end of week (Sunday)
        week_end = week_start + timedelta(days=6)

        total = (
            db.query(func.sum(UserDailyUsage.minutes_spent))
            .filter(
                and_(
                    UserDailyUsage.user_id == user_id,
                    UserDailyUsage.date >= week_start,
                    UserDailyUsage.date <= week_end,
                )
            )
            .scalar()
        )

        return total or 0, week_start, week_end

    @staticmethod
    def get_month_usage(db: Session, user_id: int) -> int:
        """Get total minutes spent this month"""
        today = date.today()

        total = (
            db.query(func.sum(UserDailyUsage.minutes_spent))
            .filter(
                and_(
                    UserDailyUsage.user_id == user_id,
                    extract("year", UserDailyUsage.date) == today.year,
                    extract("month", UserDailyUsage.date) == today.month,
                )
            )
            .scalar()
        )

        return total or 0

    @staticmethod
    def get_range_usage(
        db: Session, user_id: int, start_date: date, end_date: date
    ) -> int:
        """Get total minutes spent in a custom date range"""
        total = (
            db.query(func.sum(UserDailyUsage.minutes_spent))
            .filter(
                and_(
                    UserDailyUsage.user_id == user_id,
                    UserDailyUsage.date >= start_date,
                    UserDailyUsage.date <= end_date,
                )
            )
            .scalar()
        )

        return total or 0

    @staticmethod
    def cleanup_old_months(db: Session) -> int:
        """
        Delete all usage records from previous months.
        Returns the number of deleted records.
        """
        today = date.today()
        first_day_of_month = date(today.year, today.month, 1)

        deleted = (
            db.query(UserDailyUsage)
            .filter(UserDailyUsage.date < first_day_of_month)
            .delete()
        )

        db.commit()
        return deleted

    @staticmethod
    def get_chart_data(
        db: Session, user_id: int, start_date: date, end_date: date
    ) -> dict:
        """
        Get daily breakdown for a date range, filling in missing days with 0.
        """
        # 1. Query existing records within range
        records = (
            db.query(UserDailyUsage)
            .filter(
                and_(
                    UserDailyUsage.user_id == user_id,
                    UserDailyUsage.date >= start_date,
                    UserDailyUsage.date <= end_date,
                )
            )
            .all()
        )

        # 2. Convert DB records to a dictionary for fast lookup: { date: minutes }
        usage_map = {record.date: record.minutes_spent for record in records}

        # 3. Generate the continuous list of days (filling gaps with 0)
        chart_data = []
        total_minutes = 0
        current_date = start_date

        while current_date <= end_date:
            minutes = usage_map.get(current_date, 0)

            chart_data.append({"date": current_date, "minutes": minutes})

            total_minutes += minutes
            current_date += timedelta(days=1)

        return {"data": chart_data, "total_minutes": total_minutes}
