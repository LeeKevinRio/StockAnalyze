"""APScheduler setup for periodic data synchronization tasks."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level scheduler instance
_scheduler: AsyncIOScheduler | None = None


async def sync_prices_job() -> None:
    """Job: sync daily stock prices from TWSE.

    Runs daily at 14:30 TW time (after market close at 13:30).
    """
    logger.info("Running sync_prices_job ...")
    try:
        from app.database import async_session_factory
        from app.services.stock_service import sync_daily_prices

        async with async_session_factory() as session:
            count = await sync_daily_prices(session)
            await session.commit()
            logger.info("sync_prices_job completed: %d records", count)
    except Exception:
        logger.exception("sync_prices_job failed")


async def fetch_news_job() -> None:
    """Job: fetch latest news for tracked stocks.

    Runs every 30 minutes during market hours (09:00-14:00 TW).
    This is a placeholder that processes a subset of popular stocks.
    """
    logger.info("Running fetch_news_job ...")
    try:
        from sqlalchemy import select

        from app.database import async_session_factory
        from app.models.stock import Stock
        from app.services.news_service import fetch_and_store_news

        async with async_session_factory() as session:
            # Fetch news for a batch of stocks (top-listed as a simple heuristic)
            stmt = select(Stock).limit(20)
            result = await session.execute(stmt)
            stocks = result.scalars().all()

            total_new = 0
            for stock in stocks:
                count = await fetch_and_store_news(
                    stock.stock_id, stock.name, session
                )
                total_new += count

            await session.commit()
            logger.info("fetch_news_job completed: %d new articles", total_new)
    except Exception:
        logger.exception("fetch_news_job failed")


async def fetch_social_job() -> None:
    """Job: fetch and analyze social media posts.

    Runs every 2 hours around the clock.
    """
    logger.info("Running fetch_social_job ...")
    try:
        from app.database import async_session_factory
        from app.services.sentiment_service import fetch_and_analyze_social

        async with async_session_factory() as session:
            count = await fetch_and_analyze_social(session)
            await session.commit()
            logger.info("fetch_social_job completed: %d new posts", count)
    except Exception:
        logger.exception("fetch_social_job failed")


def start_scheduler() -> None:
    """Initialize and start the APScheduler with all registered jobs.

    The scheduler is only started when ``settings.SCHEDULER_ENABLED`` is
    ``True``.  Calling this multiple times is safe — subsequent calls are
    no-ops if the scheduler is already running.
    """
    global _scheduler

    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler is disabled via SCHEDULER_ENABLED=False")
        return

    if _scheduler is not None and _scheduler.running:
        logger.info("Scheduler is already running")
        return

    _scheduler = AsyncIOScheduler()

    # Daily price sync at 14:30 TW time (UTC+8 -> 06:30 UTC)
    _scheduler.add_job(
        sync_prices_job,
        trigger=CronTrigger(hour=14, minute=30, timezone="Asia/Taipei"),
        id="sync_prices",
        name="Sync daily stock prices",
        replace_existing=True,
    )

    # News fetch every 30 min during market hours (09:00-14:00 TW)
    _scheduler.add_job(
        fetch_news_job,
        trigger=CronTrigger(
            hour="9-13",
            minute="0,30",
            timezone="Asia/Taipei",
        ),
        id="fetch_news",
        name="Fetch stock news",
        replace_existing=True,
    )

    # Social media fetch every 2 hours
    _scheduler.add_job(
        fetch_social_job,
        trigger=IntervalTrigger(hours=2),
        id="fetch_social",
        name="Fetch social media posts",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Scheduler started with %d jobs", len(_scheduler.get_jobs()))


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler if it is running."""
    global _scheduler

    if _scheduler is None or not _scheduler.running:
        logger.info("Scheduler is not running — nothing to stop")
        return

    _scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")
    _scheduler = None
