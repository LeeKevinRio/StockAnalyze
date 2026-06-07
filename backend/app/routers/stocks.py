"""Stock-related API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.analysis import AnalysisReport
from app.models.stock import Stock, StockPrice
from app.schemas.stock import StockResponse, StockPriceResponse, StockDetailResponse, StockSearchResult

router = APIRouter()


@router.get("/search", response_model=list[StockSearchResult])
async def search_stocks(
    q: str = Query(..., min_length=1, description="Search query (stock ID or name)"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Search stocks by ID or name."""
    query = (
        select(Stock)
        .where(
            (Stock.stock_id.ilike(f"%{q}%")) | (Stock.name.ilike(f"%{q}%"))
        )
        .limit(limit)
    )
    result = await db.execute(query)
    stocks = result.scalars().all()
    return stocks


@router.get("/hot", response_model=list[StockSearchResult])
async def get_hot_stocks(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get most discussed stocks (by recent sentiment mentions)."""
    # For now, return top stocks by name; will be enhanced with sentiment data later
    query = select(Stock).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/hot-detailed")
async def get_hot_detailed(
    limit: int = Query(12, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Hot stocks with latest price, change, sparkline and analysis signal.

    Returns the stocks that actually have price data (excluding the market
    index), sorted by absolute daily change so the most active appear first.
    """
    ids = (
        await db.execute(
            select(StockPrice.stock_id).where(StockPrice.stock_id != "TAIEX").distinct()
        )
    ).scalars().all()

    out = []
    for sid in ids:
        prices = (
            await db.execute(
                select(StockPrice)
                .where(StockPrice.stock_id == sid)
                .order_by(StockPrice.date.desc())
                .limit(20)
            )
        ).scalars().all()
        if not prices:
            continue
        prices = list(reversed(prices))  # ascending
        closes = [float(p.close) for p in prices if p.close is not None]
        if not closes:
            continue
        latest = closes[-1]
        prev = closes[-2] if len(closes) >= 2 else latest
        change = latest - prev
        change_pct = (change / prev * 100) if prev else 0.0

        stock = (
            await db.execute(select(Stock).where(Stock.stock_id == sid))
        ).scalar_one_or_none()
        report = (
            await db.execute(
                select(AnalysisReport)
                .where(AnalysisReport.stock_id == sid)
                .order_by(AnalysisReport.report_date.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        out.append(
            {
                "stock_id": sid,
                "name": stock.name if stock else sid,
                "close": round(latest, 2),
                "change": round(change, 2),
                "change_percent": round(change_pct, 2),
                "signal": report.overall_signal if report else None,
                "sparkline": [round(c, 2) for c in closes],
            }
        )

    out.sort(key=lambda x: abs(x["change_percent"]), reverse=True)
    return out[:limit]


@router.get("/{stock_id}", response_model=StockDetailResponse)
async def get_stock_detail(
    stock_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get stock detail with latest price."""
    # Get stock info
    stock_result = await db.execute(
        select(Stock).where(Stock.stock_id == stock_id)
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Stock {stock_id} not found")

    # Get latest price
    price_result = await db.execute(
        select(StockPrice)
        .where(StockPrice.stock_id == stock_id)
        .order_by(StockPrice.date.desc())
        .limit(1)
    )
    latest_price = price_result.scalar_one_or_none()

    return StockDetailResponse(
        stock=StockResponse.model_validate(stock),
        latest_price=StockPriceResponse.model_validate(latest_price) if latest_price else None,
    )


@router.get("/{stock_id}/prices", response_model=list[StockPriceResponse])
async def get_stock_prices(
    stock_id: str,
    days: int = Query(60, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get historical price data."""
    query = (
        select(StockPrice)
        .where(StockPrice.stock_id == stock_id)
        .order_by(StockPrice.date.desc())
        .limit(days)
    )
    result = await db.execute(query)
    prices = result.scalars().all()
    return prices
