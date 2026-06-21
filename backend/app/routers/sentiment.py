"""Sentiment-related API endpoints."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.news import StockNews
from app.models.social import SocialPost, StockSentiment
from app.models.stock import Stock
from app.schemas.sentiment import (
    SentimentSummary,
    SentimentTrend,
    HotStock,
    SocialPostResponse,
)

router = APIRouter()


@router.get("/{stock_id}", response_model=SentimentSummary)
async def get_stock_sentiment(
    stock_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Latest sentiment summary, computed live from stored news + social posts.

    (The pre-aggregated stock_sentiments table isn't populated, so we average
    the per-article / per-post sentiment scores on the fly.)
    """
    today = date.today()

    # --- News sentiment (recent articles, which already carry a score) ---
    news_rows = (
        await db.execute(
            select(StockNews.sentiment, StockNews.sentiment_score)
            .where(StockNews.stock_id == stock_id, StockNews.sentiment_score.isnot(None))
            .order_by(StockNews.published_at.desc().nullslast())
            .limit(100)
        )
    ).all()
    news_scores = [float(s) for (_lbl, s) in news_rows if s is not None]
    news_sentiment = round(sum(news_scores) / len(news_scores), 3) if news_scores else None
    news_count = len(news_rows)

    # --- Social sentiment (best-effort; posts mentioning this stock) ---
    social_sentiment = None
    social_count = 0
    try:
        soc = (
            await db.execute(
                select(SocialPost.sentiment_score)
                .where(
                    SocialPost.sentiment_score.isnot(None),
                    SocialPost.mentioned_stocks.contains([stock_id]),
                )
                .limit(300)
            )
        ).scalars().all()
        ss = [float(x) for x in soc if x is not None]
        if ss:
            social_sentiment = round(sum(ss) / len(ss), 3)
            social_count = len(ss)
    except Exception:
        pass

    # --- Combined (news 0.6 / social 0.4) ---
    if news_sentiment is not None and social_sentiment is not None:
        combined_sentiment = round(news_sentiment * 0.6 + social_sentiment * 0.4, 3)
    else:
        combined_sentiment = news_sentiment if news_sentiment is not None else social_sentiment

    mention_count = news_count + social_count
    heat_level = "hot" if mention_count >= 50 else "warm" if mention_count >= 15 else "cold"

    return SentimentSummary(
        stock_id=stock_id,
        date=today,
        news_sentiment=news_sentiment,
        social_sentiment=social_sentiment,
        combined_sentiment=combined_sentiment,
        mention_count=mention_count,
        heat_level=heat_level,
    )


@router.get("/{stock_id}/trend", response_model=list[SentimentTrend])
async def get_sentiment_trend(
    stock_id: str,
    days: int = Query(30, ge=1, le=90),
    source_type: str = Query("combined", regex="^(news|social|combined)$"),
    db: AsyncSession = Depends(get_db),
):
    """Get sentiment trend over time."""
    since = date.today() - timedelta(days=days)
    query = (
        select(StockSentiment)
        .where(
            StockSentiment.stock_id == stock_id,
            StockSentiment.source_type == source_type,
            StockSentiment.date >= since,
        )
        .order_by(StockSentiment.date)
    )
    result = await db.execute(query)
    sentiments = result.scalars().all()

    return [
        SentimentTrend(
            date=str(s.date),
            score=float(s.sentiment_score or 0),
            source_type=s.source_type,
            mention_count=s.mention_count,
        )
        for s in sentiments
    ]


@router.get("/{stock_id}/social", response_model=list[SocialPostResponse])
async def get_stock_social_posts(
    stock_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get social media posts mentioning this stock."""
    query = (
        select(SocialPost)
        .where(SocialPost.mentioned_stocks.contains([stock_id]))
        .order_by(SocialPost.posted_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/hot-stocks", response_model=list[HotStock])
async def get_hot_stocks(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get stocks with highest social media activity."""
    today = date.today()
    query = (
        select(
            StockSentiment.stock_id,
            func.sum(StockSentiment.mention_count).label("total_mentions"),
            func.avg(StockSentiment.sentiment_score).label("avg_sentiment"),
        )
        .where(
            StockSentiment.source_type == "combined",
            StockSentiment.date >= today - timedelta(days=3),
        )
        .group_by(StockSentiment.stock_id)
        .order_by(func.sum(StockSentiment.mention_count).desc())
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()

    hot_stocks = []
    for row in rows:
        # Get stock name
        stock_result = await db.execute(
            select(Stock.name).where(Stock.stock_id == row.stock_id)
        )
        stock_name = stock_result.scalar_one_or_none() or row.stock_id

        mentions = row.total_mentions or 0
        heat = "hot" if mentions >= 50 else ("normal" if mentions >= 10 else "cold")

        hot_stocks.append(HotStock(
            stock_id=row.stock_id,
            stock_name=stock_name,
            mention_count=mentions,
            sentiment_score=float(row.avg_sentiment or 0),
            heat_level=heat,
        ))

    return hot_stocks
