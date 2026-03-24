"""Technical analysis API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stock import StockPrice
from app.schemas.technical import (
    TechnicalIndicatorsResponse,
    TechnicalSignal,
    TechnicalSignalsResponse,
)
from app.services.technical_service import technical_service

logger = logging.getLogger(__name__)

router = APIRouter()


async def _fetch_prices(
    stock_id: str,
    days: int,
    db: AsyncSession,
) -> list[dict]:
    """Fetch OHLCV price data from DB, returned sorted by date ascending."""
    stmt = (
        select(StockPrice)
        .where(StockPrice.stock_id == stock_id)
        .order_by(StockPrice.date.desc())
        .limit(days)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"找不到股票 {stock_id} 的價格資料",
        )

    # Convert to dicts sorted by date ascending
    prices = []
    for row in reversed(rows):
        prices.append({
            "date": row.date.isoformat() if row.date else "",
            "open": float(row.open) if row.open is not None else None,
            "high": float(row.high) if row.high is not None else None,
            "low": float(row.low) if row.low is not None else None,
            "close": float(row.close) if row.close is not None else None,
            "volume": int(row.volume) if row.volume is not None else None,
        })
    return prices


@router.get(
    "/{stock_id}",
    response_model=TechnicalIndicatorsResponse,
    summary="取得技術指標與訊號",
    description="計算完整技術指標（MA, MACD, RSI, KD, 布林通道）及買賣訊號",
)
async def get_technical_indicators(
    stock_id: str,
    days: int = Query(120, ge=30, le=365, description="分析天數（需至少60天以計算MA60）"),
    db: AsyncSession = Depends(get_db),
):
    """Get full technical indicators, signals, and score for a stock."""
    prices = await _fetch_prices(stock_id, days, db)

    result = technical_service.calculate_all(prices)

    return TechnicalIndicatorsResponse(
        stock_id=stock_id,
        indicators=result.indicators,
        signals=[
            TechnicalSignal(**s) for s in result.signals
        ],
        score=result.score,
        summary=result.summary,
    )


@router.get(
    "/{stock_id}/signals",
    response_model=TechnicalSignalsResponse,
    summary="取得買賣訊號",
    description="僅回傳技術分析偵測到的買賣訊號與評分",
)
async def get_technical_signals(
    stock_id: str,
    days: int = Query(120, ge=30, le=365, description="分析天數"),
    db: AsyncSession = Depends(get_db),
):
    """Get buy/sell signals only (lighter response without raw indicators)."""
    prices = await _fetch_prices(stock_id, days, db)

    result = technical_service.calculate_all(prices)

    return TechnicalSignalsResponse(
        stock_id=stock_id,
        signals=[
            TechnicalSignal(**s) for s in result.signals
        ],
        score=result.score,
        summary=result.summary,
    )
