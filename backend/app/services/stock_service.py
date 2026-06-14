"""Stock data service — syncing stock lists and prices from TWSE."""

import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_fetchers.twse_fetcher import TWSEFetcher
from app.models.stock import Stock, StockPrice
from app.utils.date_utils import get_last_trading_day

logger = logging.getLogger(__name__)

# Shared fetcher instance
_twse_fetcher = TWSEFetcher()


async def sync_stock_list(db: AsyncSession) -> int:
    """Fetch the TWSE stock list and upsert into the ``stocks`` table.

    New stocks are inserted; existing stocks have their name and
    industry updated.

    Args:
        db: Async database session.

    Returns:
        Total number of stocks processed (inserted + updated).
    """
    info_list = await _twse_fetcher.fetch_stock_info()
    if not info_list:
        logger.warning("TWSE returned empty stock info list")
        return 0

    count = 0
    for info in info_list:
        stock_id = info.get("stock_id", "").strip()
        if not stock_id:
            continue

        stmt = select(Stock).where(Stock.stock_id == stock_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        name = info.get("name", "").strip()
        industry = info.get("industry", "").strip() or None
        market = info.get("market", "TWSE")
        listed_date_str = info.get("listed_date", "")

        listed_date = _parse_listed_date(listed_date_str)

        if existing:
            existing.name = name or existing.name
            existing.industry = industry or existing.industry
            existing.market = market
            if listed_date:
                existing.listed_date = listed_date
        else:
            db.add(
                Stock(
                    stock_id=stock_id,
                    name=name,
                    industry=industry,
                    market=market,
                    listed_date=listed_date,
                )
            )
        count += 1

    await db.flush()
    logger.info("Synced %d stocks from TWSE", count)
    return count


async def sync_daily_prices(
    db: AsyncSession,
    target_date: date | None = None,
) -> int:
    """Fetch daily OHLCV prices and store in the ``stock_prices`` table.

    Duplicate entries (same stock_id + date) are skipped.

    Args:
        db: Async database session.
        target_date: The trading date to sync. Defaults to the last
            trading day.

    Returns:
        Number of newly inserted price records.
    """
    if target_date is None:
        target_date = get_last_trading_day()

    date_str = target_date.strftime("%Y%m%d")
    prices = await _twse_fetcher.fetch_daily_prices(date_str)
    if not prices:
        logger.warning("No daily price data returned for %s", date_str)
        return 0

    new_count = 0
    for row in prices:
        stock_id = row.get("stock_id", "").strip()
        if not stock_id:
            continue

        # Check for existing record
        stmt = select(StockPrice.id).where(
            StockPrice.stock_id == stock_id,
            StockPrice.date == target_date,
        ).limit(1)
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            continue

        open_price = _safe_decimal(row.get("open"))
        high_price = _safe_decimal(row.get("high"))
        low_price = _safe_decimal(row.get("low"))
        close_price = _safe_decimal(row.get("close"))
        volume = _safe_int(row.get("volume"))
        change = _safe_decimal(row.get("change"))

        # Compute change_percent if we have close and change
        change_percent: Decimal | None = None
        if close_price and change:
            prev_close = close_price - change
            if prev_close != 0:
                change_percent = Decimal(
                    str(round(float(change / prev_close * 100), 2))
                )

        db.add(
            StockPrice(
                stock_id=stock_id,
                date=target_date,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
                change_percent=change_percent,
            )
        )
        new_count += 1

    await db.flush()
    logger.info("Stored %d new price records for %s", new_count, date_str)
    return new_count


# Per-stock locks so concurrent requests don't double-fetch the same stock.
import asyncio as _asyncio

_price_locks: dict[str, "_asyncio.Lock"] = {}


async def ensure_price_history(
    stock_id: str,
    db: AsyncSession,
    days: int = 180,
) -> int:
    """On-demand backfill: if a stock has no price history, fetch ~6 months
    from FinMind and store it. Safe to call concurrently (per-stock lock).

    FinMind is used instead of yfinance because Yahoo Finance blocks
    datacenter IPs (e.g. Render), whereas FinMind works from the cloud.

    Returns the number of rows inserted (0 if data already existed or none
    was available).
    """
    from datetime import timedelta

    import httpx

    exists = (
        await db.execute(
            select(StockPrice.id).where(StockPrice.stock_id == stock_id).limit(1)
        )
    ).scalar_one_or_none()
    if exists is not None:
        return 0

    lock = _price_locks.setdefault(stock_id, _asyncio.Lock())
    async with lock:
        # Re-check after acquiring the lock (another request may have filled it).
        exists = (
            await db.execute(
                select(StockPrice.id).where(StockPrice.stock_id == stock_id).limit(1)
            )
        ).scalar_one_or_none()
        if exists is not None:
            return 0

        start = (date.today() - timedelta(days=days)).isoformat()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    "https://api.finmindtrade.com/api/v4/data",
                    params={"dataset": "TaiwanStockPrice", "data_id": stock_id, "start_date": start},
                )
                resp.raise_for_status()
                payload = resp.json()
        except Exception:
            logger.exception("FinMind price fetch failed for %s", stock_id)
            return 0

        if payload.get("msg") != "success" or not payload.get("data"):
            logger.info("No FinMind price data for %s", stock_id)
            return 0

        n = 0
        for row in payload["data"]:
            try:
                db.add(
                    StockPrice(
                        stock_id=stock_id,
                        date=date.fromisoformat(row["date"]),
                        open=Decimal(str(round(float(row["open"]), 2))),
                        high=Decimal(str(round(float(row["max"]), 2))),
                        low=Decimal(str(round(float(row["min"]), 2))),
                        close=Decimal(str(round(float(row["close"]), 2))),
                        volume=int(row.get("Trading_Volume") or 0),
                    )
                )
                n += 1
            except (TypeError, ValueError, InvalidOperation, KeyError):
                continue
        await db.commit()
        logger.info("On-demand backfilled %d price rows for %s (FinMind)", n, stock_id)
        return n


async def get_stock(stock_id: str, db: AsyncSession) -> Stock | None:
    """Retrieve a single stock by its ID.

    Args:
        stock_id: Taiwan stock ID (e.g. ``"2330"``).
        db: Async database session.

    Returns:
        The ``Stock`` instance or ``None`` if not found.
    """
    stmt = select(Stock).where(Stock.stock_id == stock_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def search_stocks(
    query: str,
    db: AsyncSession,
    limit: int = 10,
) -> list[Stock]:
    """Search stocks by ID prefix or name substring.

    Args:
        query: Search term — matched against stock_id (prefix) and
            name (contains).
        db: Async database session.
        limit: Maximum number of results.

    Returns:
        List of matching ``Stock`` instances.
    """
    pattern = f"%{query}%"
    stmt = (
        select(Stock)
        .where(
            or_(
                Stock.stock_id.startswith(query),
                Stock.name.ilike(pattern),
            )
        )
        .order_by(Stock.stock_id)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _safe_decimal(value: str | None) -> Decimal | None:
    """Convert a string value to Decimal, returning None on failure."""
    if not value:
        return None
    # TWSE sometimes uses commas in numbers
    cleaned = value.replace(",", "").strip()
    if not cleaned or cleaned == "--":
        return None
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _safe_int(value: str | None) -> int | None:
    """Convert a string value to int, returning None on failure."""
    if not value:
        return None
    cleaned = value.replace(",", "").strip()
    if not cleaned or cleaned == "--":
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def _parse_listed_date(date_str: str) -> date | None:
    """Parse TWSE listed date formats (e.g. ``'2024/01/15'`` or ``'1130115'`` ROC)."""
    if not date_str:
        return None
    date_str = date_str.strip()

    # Try standard format: YYYY/MM/DD
    if "/" in date_str:
        parts = date_str.split("/")
        if len(parts) == 3:
            try:
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                # Convert ROC year to AD if needed
                if year < 1911:
                    year += 1911
                return date(year, month, day)
            except (ValueError, OverflowError):
                return None

    # Try ROC format: YYYMMDD (e.g. 1130115 = 2024/01/15)
    if len(date_str) == 7 and date_str.isdigit():
        try:
            roc_year = int(date_str[:3])
            month = int(date_str[3:5])
            day = int(date_str[5:7])
            return date(roc_year + 1911, month, day)
        except (ValueError, OverflowError):
            return None

    return None
