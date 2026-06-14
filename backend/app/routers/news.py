"""News-related API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models.news import StockNews
from app.schemas.news import NewsResponse, NewsSentimentTrend

router = APIRouter()


@router.get("/market", response_model=list[NewsResponse])
async def get_market_news(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get market-wide news."""
    query = (
        select(StockNews)
        .order_by(StockNews.published_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{stock_id}", response_model=list[NewsResponse])
async def get_stock_news(
    stock_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get news for a specific stock."""
    def _query():
        return (
            select(StockNews)
            .where(StockNews.stock_id == stock_id)
            .order_by(StockNews.published_at.desc())
            .limit(limit)
        )

    result = await db.execute(_query())
    rows = result.scalars().all()

    # On-demand: fetch news (with sentiment) the first time a stock is viewed.
    if not rows:
        from app.models.stock import Stock
        from app.services.news_service import fetch_and_store_news
        stock = (await db.execute(select(Stock).where(Stock.stock_id == stock_id))).scalar_one_or_none()
        if stock:
            try:
                await fetch_and_store_news(stock_id, stock.name, db)
                await db.commit()
                rows = (await db.execute(_query())).scalars().all()
            except Exception:
                pass

    return rows


@router.get("/{stock_id}/sentiment-trend", response_model=list[NewsSentimentTrend])
async def get_news_sentiment_trend(
    stock_id: str,
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Get news sentiment trend over time."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        select(
            func.date(StockNews.published_at).label("date"),
            func.avg(StockNews.sentiment_score).label("sentiment_score"),
            func.count().label("article_count"),
            func.sum(case((StockNews.sentiment == "positive", 1), else_=0)).label("positive_count"),
            func.sum(case((StockNews.sentiment == "negative", 1), else_=0)).label("negative_count"),
            func.sum(case((StockNews.sentiment == "neutral", 1), else_=0)).label("neutral_count"),
        )
        .where(
            StockNews.stock_id == stock_id,
            StockNews.published_at >= since,
        )
        .group_by(func.date(StockNews.published_at))
        .order_by(func.date(StockNews.published_at))
    )
    result = await db.execute(query)
    rows = result.all()

    return [
        NewsSentimentTrend(
            date=str(row.date),
            sentiment_score=float(row.sentiment_score or 0),
            article_count=row.article_count,
            positive_count=row.positive_count or 0,
            negative_count=row.negative_count or 0,
            neutral_count=row.neutral_count or 0,
        )
        for row in rows
    ]
