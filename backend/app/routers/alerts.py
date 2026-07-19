"""Price alerts + notification center endpoints.

Users create "notify me when close crosses X" alerts; the daily cron hits
POST /check after the data refresh, which flips crossed alerts to triggered.
Triggered alerts surface in the 通知中心 page (no email required).
"""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stock import Stock, StockPrice
from app.models.user import PriceAlert, User
from app.services.auth_service import get_current_user

router = APIRouter()


class AlertInput(BaseModel):
    stock_id: str = Field(..., min_length=1, max_length=10)
    condition: str = Field(..., pattern="^(above|below)$")
    target_price: float = Field(..., gt=0)


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


def _crossed(condition: str, close: float, target: float) -> bool:
    return close >= target if condition == "above" else close <= target


@router.get("")
async def get_alerts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """All of the user's alerts — active first, then triggered (newest first)."""
    alerts = (
        await db.execute(
            select(PriceAlert)
            .where(PriceAlert.user_id == user.id)
            .order_by(PriceAlert.active.desc(), PriceAlert.created_at.desc())
        )
    ).scalars().all()

    out = []
    for a in alerts:
        stock = (
            await db.execute(select(Stock).where(Stock.stock_id == a.stock_id))
        ).scalar_one_or_none()
        out.append({
            "id": a.id,
            "stock_id": a.stock_id,
            "name": stock.name if stock else a.stock_id,
            "condition": a.condition,
            "target_price": float(a.target_price),
            "active": a.active,
            "close": await _latest_close(a.stock_id, db),
            "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
            "triggered_price": float(a.triggered_price) if a.triggered_price is not None else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return out


@router.post("")
async def create_alert(
    body: AlertInput,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stock_id = body.stock_id.strip()
    stock = (
        await db.execute(select(Stock).where(Stock.stock_id == stock_id))
    ).scalar_one_or_none()
    if stock is None:
        raise HTTPException(status_code=404, detail=f"Stock {stock_id} not found")

    db.add(PriceAlert(
        user_id=user.id,
        stock_id=stock_id,
        condition=body.condition,
        target_price=Decimal(str(round(body.target_price, 2))),
        active=True,
    ))
    await db.commit()
    return {"ok": True}


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(PriceAlert).where(
            PriceAlert.id == alert_id, PriceAlert.user_id == user.id
        )
    )
    await db.commit()
    return {"ok": True}


@router.post("/check")
async def check_alerts(db: AsyncSession = Depends(get_db)):
    """Evaluate all active alerts against the latest close (cron calls this).

    Unauthenticated by design: it reveals nothing and only flips alerts whose
    condition is already met by public market data.
    """
    alerts = (
        await db.execute(select(PriceAlert).where(PriceAlert.active.is_(True)))
    ).scalars().all()

    triggered = 0
    closes: dict[str, float | None] = {}
    for a in alerts:
        if a.stock_id not in closes:
            closes[a.stock_id] = await _latest_close(a.stock_id, db)
        close = closes[a.stock_id]
        if close is None:
            continue
        if _crossed(a.condition, close, float(a.target_price)):
            a.active = False
            a.triggered_at = datetime.now(timezone.utc)
            a.triggered_price = Decimal(str(round(close, 2)))
            triggered += 1
    if triggered:
        await db.commit()
    return {"checked": len(alerts), "triggered": triggered}
