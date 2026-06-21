"""Per-user watchlist endpoints (require authentication)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, WatchlistItem
from app.services.auth_service import get_current_user

router = APIRouter()


@router.get("")
async def get_watchlist(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """Return the current user's watchlist stock IDs (most recent first)."""
    rows = (
        await db.execute(
            select(WatchlistItem.stock_id)
            .where(WatchlistItem.user_id == user.id)
            .order_by(WatchlistItem.created_at.desc())
        )
    ).scalars().all()
    return list(rows)


@router.post("/{stock_id}")
async def add_to_watchlist(
    stock_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stock_id = stock_id.strip()
    existing = (
        await db.execute(
            select(WatchlistItem).where(
                WatchlistItem.user_id == user.id, WatchlistItem.stock_id == stock_id
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(WatchlistItem(user_id=user.id, stock_id=stock_id))
        await db.commit()
    return {"ok": True, "stock_id": stock_id}


@router.delete("/{stock_id}")
async def remove_from_watchlist(
    stock_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(WatchlistItem).where(
            WatchlistItem.user_id == user.id, WatchlistItem.stock_id == stock_id.strip()
        )
    )
    await db.commit()
    return {"ok": True, "stock_id": stock_id}
