"""Sentiment-related API endpoints."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
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
    """Get latest sentiment summary for a stock."""
    today = date.today()
    query = (
        select(StockSentiment)
        .where(
            StockSentiment.stock_id == stock_id,
            StockSentiment.date >= today - timedelta(days=7),
        )
        .order_by(StockSentiment.date.desc())
    )
    result = await db.execute(query)
    sentiments = result.scalars().all()

    news_sentiment = None
    social_sentiment = None
    combined_sentiment = None
    mention_count = 0
    heat_level = "cold"

    for s in sentiments:
        if s.source_type == "news" and news_sentiment is None:
            news_sentiment = s.sentiment_score
        elif s.source_type == "social" and social_sentiment is None:
            social_sentiment = s.sentiment_score
        elif s.source_type == "combined" and combined_sentiment is None:
            combined_sentiment = s.sentiment_score
            mention_count = s.mention_count
            heat_level = s.heat_level or "cold"

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
