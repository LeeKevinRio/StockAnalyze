"""News aggregation service — fetching, deduplication, and persistence."""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_fetchers.news_fetcher import NewsFetcher
from app.models.news import StockNews
from app.services.sentiment_analyzer import ChineseSentimentAnalyzer
from app.utils.text_utils import title_similarity

logger = logging.getLogger(__name__)

# Similarity threshold to consider two titles the same article
_DEDUP_THRESHOLD = 0.7

# Shared fetcher instance (stateless aside from rate-limit bookkeeping)
_news_fetcher = NewsFetcher()

# Lexicon-based sentiment analyzer (synchronous, no API key required)
_sentiment_analyzer = ChineseSentimentAnalyzer()


def _impact_from_score(score: float) -> str:
    """Derive a coarse impact level from the absolute sentiment magnitude."""
    a = abs(score)
    if a >= 0.6:
        return "high"
    if a >= 0.3:
        return "medium"
    return "low"


async def fetch_and_store_news(
    stock_id: str,
    stock_name: str,
    db: AsyncSession,
) -> int:
    """Fetch news from all sources and persist new articles.

    Existing articles in the database are used for deduplication so that
    only genuinely new articles are inserted.

    Args:
        stock_id: Taiwan stock ID (e.g. ``"2330"``).
        stock_name: Human-readable stock name (used as search query).
        db: Async database session.

    Returns:
        The number of newly inserted articles.
    """
    articles = await _news_fetcher.fetch_all_news(stock_id, stock_name)
    if not articles:
        return 0

    # Load recent titles from the DB for dedup
    stmt = (
        select(StockNews.title)
        .where(StockNews.stock_id == stock_id)
        .order_by(StockNews.fetched_at.desc())
        .limit(200)
    )
    result = await db.execute(stmt)
    existing_titles: list[str] = [row[0] for row in result.all()]

    new_count = 0
    for article in articles:
        title = article.get("title", "")
        if not title:
            continue

        # Check against DB titles
        is_dup = any(
            title_similarity(title, existing) >= _DEDUP_THRESHOLD
            for existing in existing_titles
        )
        if is_dup:
            continue

        # Sentiment analysis on title + content (lexicon-based, no API key).
        analysis_text = f"{title}。{article.get('content') or ''}"
        sent = _sentiment_analyzer.analyze(analysis_text)

        news_record = StockNews(
            stock_id=stock_id,
            title=title,
            content=article.get("content"),
            source=article.get("source"),
            source_url=article.get("source_url"),
            published_at=article.get("published_at"),
            sentiment=sent.label,
            sentiment_score=round(sent.score, 3),
            sentiment_method="keyword",
            impact_level=_impact_from_score(sent.score),
        )
        db.add(news_record)
        existing_titles.append(title)
        new_count += 1

    if new_count:
        await db.flush()

    logger.info(
        "Stored %d new news articles for %s (%s)", new_count, stock_id, stock_name
    )
    return new_count


async def get_stock_news(
    stock_id: str,
    db: AsyncSession,
    limit: int = 20,
) -> list[StockNews]:
    """Retrieve the most recent news articles for a given stock.

    Args:
        stock_id: Taiwan stock ID.
        db: Async database session.
        limit: Maximum number of articles to return.

    Returns:
        List of ``StockNews`` model instances ordered by recency.
    """
    stmt = (
        select(StockNews)
        .where(StockNews.stock_id == stock_id)
        .order_by(StockNews.published_at.desc().nullslast())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_market_news(
    db: AsyncSession,
    limit: int = 50,
) -> list[StockNews]:
    """Retrieve the most recent market-wide news articles.

    Market-wide articles are those with ``stock_id IS NULL`` or any
    recently published article regardless of stock affiliation.

    Args:
        db: Async database session.
        limit: Maximum number of articles to return.

    Returns:
        List of ``StockNews`` model instances ordered by recency.
    """
    stmt = (
        select(StockNews)
        .order_by(StockNews.published_at.desc().nullslast())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
