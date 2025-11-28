import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.database import SessionLocal
from app.services.user_daily_usage import UsageService

logger = logging.getLogger(__name__)


def cleanup_old_usage_data():
    """
    Scheduled task to clean up old usage data.
    Deletes all records from previous months.
    Runs on the 1st day of each month at 00:00.
    """
    db = SessionLocal()
    try:
        deleted_count = UsageService.cleanup_old_months(db)
        logger.info(
            f"[{datetime.now(timezone.utc)}] Monthly cleanup completed. "
            f"Deleted {deleted_count} old usage records."
        )
    except Exception as e:
        logger.error(f"Error during monthly cleanup: {e}")
    finally:
        db.close()


def start_scheduler():
    """
    Initialize and start the APScheduler for monthly cleanup.
    """
    scheduler = AsyncIOScheduler()

    # Schedule monthly cleanup on 1st day at 00:00
    scheduler.add_job(
        cleanup_old_usage_data,
        trigger=CronTrigger(day=1, hour=0, minute=0),
        id="monthly_usage_cleanup",
        name="Clean up old usage data",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Usage tracking scheduler started. Monthly cleanup scheduled.")

    return scheduler


def shutdown_scheduler(scheduler: AsyncIOScheduler):
    """
    Gracefully shutdown the scheduler.
    """
    if scheduler:
        scheduler.shutdown()
        logger.info("Usage tracking scheduler shut down.")
