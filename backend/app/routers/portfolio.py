"""Per-user portfolio endpoints (require authentication).

Holdings are stored in 股 (shares) with per-share average cost; the GET
endpoint enriches each holding with the latest close so the frontend can
render P/L without extra round-trips.
"""

from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stock import Stock, StockPrice
from app.models.user import PortfolioItem, User
from app.services.auth_service import get_current_user

router = APIRouter()


class HoldingInput(BaseModel):
    quantity: int = Field(..., gt=0, description="持有股數 (股)")
    avg_cost: float = Field(..., gt=0, description="平均成本 (每股)")


async def _latest_close(stock_id: str, db: AsyncSession) -> float | None:
    price = (
        await db.execute(
            select(StockPrice.close)
            .where(StockPrice.stock_id == stock_id)
            .order_by(StockPrice.date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return float(price) if price is not None else None


@router.get("")
async def get_portfolio(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Current user's holdings with latest close and P/L."""
    items = (
        await db.execute(
            select(PortfolioItem)
            .where(PortfolioItem.user_id == user.id)
            .order_by(PortfolioItem.created_at)
        )
    ).scalars().all()

    out = []
    for it in items:
        stock = (
            await db.execute(select(Stock).where(Stock.stock_id == it.stock_id))
        ).scalar_one_or_none()
        close = await _latest_close(it.stock_id, db)
        cost = float(it.avg_cost)
        qty = int(it.quantity)
        market_value = round(close * qty, 0) if close is not None else None
        cost_value = round(cost * qty, 0)
        pnl = round(market_value - cost_value, 0) if market_value is not None else None
        pnl_pct = round((close - cost) / cost * 100, 2) if (close is not None and cost) else None
        out.append({
            "stock_id": it.stock_id,
            "name": stock.name if stock else it.stock_id,
            "quantity": qty,
            "avg_cost": cost,
            "close": close,
            "cost_value": cost_value,
            "market_value": market_value,
            "pnl": pnl,
            "pnl_percent": pnl_pct,
        })
    return out


@router.post("/{stock_id}")
async def upsert_holding(
    stock_id: str,
    body: HoldingInput,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add or update a holding (idempotent upsert by stock)."""
    stock_id = stock_id.strip()
    stock = (
        await db.execute(select(Stock).where(Stock.stock_id == stock_id))
    ).scalar_one_or_none()
    if stock is None:
        raise HTTPException(status_code=404, detail=f"Stock {stock_id} not found")

    try:
        cost = Decimal(str(round(body.avg_cost, 2)))
    except InvalidOperation:
        raise HTTPException(status_code=422, detail="Invalid avg_cost")

    existing = (
        await db.execute(
            select(PortfolioItem).where(
                PortfolioItem.user_id == user.id, PortfolioItem.stock_id == stock_id
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(PortfolioItem(
            user_id=user.id, stock_id=stock_id,
            quantity=body.quantity, avg_cost=cost,
        ))
    else:
        existing.quantity = body.quantity
        existing.avg_cost = cost
    await db.commit()
    return {"ok": True, "stock_id": stock_id}


@router.delete("/{stock_id}")
async def remove_holding(
    stock_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(PortfolioItem).where(
            PortfolioItem.user_id == user.id, PortfolioItem.stock_id == stock_id.strip()
        )
    )
    await db.commit()
    return {"ok": True, "stock_id": stock_id}
