"""Social sentiment orchestration — fetching, analysis, and aggregation."""

import logging
import re
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_fetchers.ptt_fetcher import PTTFetcher
from app.models.social import SocialPost, StockSentiment
from app.utils.date_utils import get_tw_today
from app.utils.text_utils import normalize_chinese

logger = logging.getLogger(__name__)

# Shared fetcher instance
_ptt_fetcher = PTTFetcher()

# Simple keyword-based sentiment lexicons for Taiwan stock discussions
_POSITIVE_KEYWORDS: set[str] = {
    "漲", "噴", "多", "看好", "利多", "突破", "創新高", "強勢",
    "買進", "加碼", "上漲", "紅盤", "大漲", "爆量", "起飛", "好消息",
    "樂觀", "營收成長", "獲利", "上攻",
}
_NEGATIVE_KEYWORDS: set[str] = {
    "跌", "空", "看壞", "利空", "崩", "破底", "弱勢",
    "賣出", "減碼", "下跌", "綠盤", "大跌", "套牢", "出貨", "壞消息",
    "悲觀", "虧損", "衰退", "下殺", "跳水",
}

# Sentiment weights for combined score
NEWS_WEIGHT = 0.6
SOCIAL_WEIGHT = 0.4


async def fetch_and_analyze_social(db: AsyncSession) -> int:
    """Fetch PTT posts, run keyword sentiment analysis, and store results.

    Args:
        db: Async database session.

    Returns:
        Number of newly stored social posts.
    """
    posts = await _ptt_fetcher.fetch_recent_posts(pages=3)
    if not posts:
        return 0

    new_count = 0
    for post_data in posts:
        title = post_data.get("title", "")
        url = post_data.get("url", "")

        # Skip if already stored (by URL)
        if url:
            stmt = select(SocialPost.id).where(SocialPost.url == url).limit(1)
            result = await db.execute(stmt)
            if result.scalar_one_or_none() is not None:
                continue

        # Run keyword sentiment
        sentiment_label, sentiment_score = _keyword_sentiment(
            title, post_data.get("content", "")
        )

        social_post = SocialPost(
            platform=post_data.get("platform", "ptt"),
            board=post_data.get("board", "Stock"),
            title=title,
            content=post_data.get("content", ""),
            author=post_data.get("author", ""),
            url=url,
            mentioned_stocks=post_data.get("mentioned_stocks", []),
            sentiment=sentiment_label,
            sentiment_score=sentiment_score,
            push_count=post_data.get("push_count", 0),
            boo_count=post_data.get("boo_count", 0),
            posted_at=post_data.get("posted_at"),
        )
        db.add(social_post)
        new_count += 1

    if new_count:
        await db.flush()

    logger.info("Stored %d new social posts", new_count)
    return new_count


async def get_stock_sentiment_summary(
    stock_id: str,
    db: AsyncSession,
) -> dict:
    """Get the latest sentiment summary for a stock.

    Retrieves the most recent combined, news, and social sentiment
    records and returns them in a single dict.

    Args:
        stock_id: Taiwan stock ID.
        db: Async database session.

    Returns:
        Dict with keys: stock_id, date, combined_score, news_score,
        social_score, mention_count, positive_count, negative_count,
        neutral_count, heat_level.
    """
    stmt = (
        select(StockSentiment)
        .where(
            and_(
                StockSentiment.stock_id == stock_id,
                StockSentiment.source_type == "combined",
            )
        )
        .order_by(StockSentiment.date.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    combined = result.scalar_one_or_none()

    if combined is None:
        return {
            "stock_id": stock_id,
            "date": None,
            "combined_score": None,
            "news_score": None,
            "social_score": None,
            "mention_count": 0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "heat_level": "cold",
        }

    return {
        "stock_id": stock_id,
        "date": combined.date.isoformat() if combined.date else None,
        "combined_score": float(combined.sentiment_score) if combined.sentiment_score else None,
        "news_score": None,  # Filled from separate query if needed
        "social_score": None,
        "mention_count": combined.mention_count,
        "positive_count": combined.positive_count,
        "negative_count": combined.negative_count,
        "neutral_count": combined.neutral_count,
        "heat_level": combined.heat_level,
    }


async def aggregate_daily_sentiment(
    stock_id: str,
    target_date: date,
    db: AsyncSession,
) -> None:
    """Aggregate news and social sentiment into a combined daily score.

    Reads the ``news`` and ``social`` source_type rows for the given
    stock and date, then upserts a ``combined`` row with the weighted
    average.

    Weights: news 0.6, social 0.4.

    Args:
        stock_id: Taiwan stock ID.
        target_date: The date to aggregate.
        db: Async database session.
    """
    # Fetch news sentiment for the day
    news_sent = await _get_sentiment_row(stock_id, target_date, "news", db)
    social_sent = await _get_sentiment_row(stock_id, target_date, "social", db)

    news_score = float(news_sent.sentiment_score) if news_sent and news_sent.sentiment_score else 0.0
    social_score = float(social_sent.sentiment_score) if social_sent and social_sent.sentiment_score else 0.0

    # Weighted combination
    combined_score = news_score * NEWS_WEIGHT + social_score * SOCIAL_WEIGHT

    # Aggregate counts
    mention_count = (
        (news_sent.mention_count if news_sent else 0)
        + (social_sent.mention_count if social_sent else 0)
    )
    positive_count = (
        (news_sent.positive_count if news_sent else 0)
        + (social_sent.positive_count if social_sent else 0)
    )
    negative_count = (
        (news_sent.negative_count if news_sent else 0)
        + (social_sent.negative_count if social_sent else 0)
    )
    neutral_count = (
        (news_sent.neutral_count if news_sent else 0)
        + (social_sent.neutral_count if social_sent else 0)
    )

    heat_level = _compute_heat_level(mention_count)

    # Upsert the combined row
    stmt = select(StockSentiment).where(
        and_(
            StockSentiment.stock_id == stock_id,
            StockSentiment.date == target_date,
            StockSentiment.source_type == "combined",
        )
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.sentiment_score = Decimal(str(round(combined_score, 3)))
        existing.mention_count = mention_count
        existing.positive_count = positive_count
        existing.negative_count = negative_count
        existing.neutral_count = neutral_count
        existing.heat_level = heat_level
    else:
        db.add(
            StockSentiment(
                stock_id=stock_id,
                date=target_date,
                source_type="combined",
                sentiment_score=Decimal(str(round(combined_score, 3))),
                mention_count=mention_count,
                positive_count=positive_count,
                negative_count=negative_count,
                neutral_count=neutral_count,
                heat_level=heat_level,
            )
        )

    await db.flush()
    logger.info(
        "Aggregated combined sentiment for %s on %s: %.3f",
        stock_id,
        target_date,
        combined_score,
    )


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


async def _get_sentiment_row(
    stock_id: str,
    target_date: date,
    source_type: str,
    db: AsyncSession,
) -> StockSentiment | None:
    """Fetch a single sentiment row by stock, date, and source type."""
    stmt = select(StockSentiment).where(
        and_(
            StockSentiment.stock_id == stock_id,
            StockSentiment.date == target_date,
            StockSentiment.source_type == source_type,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _keyword_sentiment(title: str, content: str) -> tuple[str, Decimal]:
    """Run keyword-based sentiment analysis on text.

    Returns:
        Tuple of (sentiment_label, sentiment_score) where label is one
        of ``"positive"``, ``"negative"``, or ``"neutral"`` and score
        is in the range [-1.000, 1.000].
    """
    text = normalize_chinese(f"{title} {content}")

    pos_hits = sum(1 for kw in _POSITIVE_KEYWORDS if kw in text)
    neg_hits = sum(1 for kw in _NEGATIVE_KEYWORDS if kw in text)

    total = pos_hits + neg_hits
    if total == 0:
        return "neutral", Decimal("0.000")

    raw_score = (pos_hits - neg_hits) / total  # range [-1, 1]
    score = Decimal(str(round(raw_score, 3)))

    if raw_score > 0.1:
        label = "positive"
    elif raw_score < -0.1:
        label = "negative"
    else:
        label = "neutral"

    return label, score


def _compute_heat_level(mention_count: int) -> str:
    """Determine heat level from total mention count."""
    if mention_count >= 20:
        return "hot"
    elif mention_count >= 5:
        return "normal"
    return "cold"
