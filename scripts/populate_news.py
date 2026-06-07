"""Populate news (and optionally social) for a set of stocks.

Fetches news from the configured RSS/news sources and stores them, so the
消息面 (news) dimension and the /news pages have real content.

Usage:
    cd backend && python ../scripts/populate_news.py
    python ../scripts/populate_news.py 2330 2317
    python ../scripts/populate_news.py --social     # also fetch PTT social posts

If no stock_ids are given, defaults to the blue-chip stocks that have price
data backfilled.
"""

import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select

from app.database import async_session_factory, init_db
from app.models.stock import Stock
from app.services.news_service import fetch_and_store_news

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_STOCKS = ["2330", "2317", "2454", "2308", "2882"]


async def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_social = "--social" in sys.argv

    stock_ids = args or DEFAULT_STOCKS

    await init_db()

    async with async_session_factory() as session:
        # Resolve names
        result = await session.execute(select(Stock).where(Stock.stock_id.in_(stock_ids)))
        stocks = {s.stock_id: s.name for s in result.scalars().all()}

        total = 0
        for sid in stock_ids:
            name = stocks.get(sid, sid)
            try:
                count = await fetch_and_store_news(sid, name, session)
                await session.commit()
                total += count
                logger.info("News %s (%s): +%d new articles", sid, name, count)
            except Exception:
                await session.rollback()
                logger.exception("News fetch failed for %s", sid)

        logger.info("=== News done: %d new articles across %d stocks ===", total, len(stock_ids))

    if do_social:
        from app.services.sentiment_service import fetch_and_analyze_social

        async with async_session_factory() as session:
            try:
                count = await fetch_and_analyze_social(session)
                await session.commit()
                logger.info("=== Social done: %d new posts ===", count)
            except Exception:
                await session.rollback()
                logger.exception("Social fetch failed")


if __name__ == "__main__":
    asyncio.run(main())
