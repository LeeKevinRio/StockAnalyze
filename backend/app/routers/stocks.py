"""Stock-related API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
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
