"""
Backfill historical stock prices for specified stocks.

Uses yfinance to fetch 6 months of daily OHLCV data and upserts
into the stock_prices table, skipping dates that already exist.

Usage:
    python scripts/backfill_prices.py [stock_ids...]

If no stock_ids provided, backfills top 5 blue-chip stocks:
    2330 (TSMC), 2317 (Hon Hai), 2454 (MediaTek), 2308 (Delta), 2882 (Cathay FHC)

Examples:
    python scripts/backfill_prices.py
    python scripts/backfill_prices.py 2330 2317
    python scripts/backfill_prices.py 2454 2882 2881
"""

import asyncio
import logging
import sys
import os
from datetime import date
from decimal import Decimal, InvalidOperation

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import yfinance as yf
from sqlalchemy import select

from app.database import async_session_factory, init_db
from app.models.stock import StockPrice

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Default stocks to backfill when none specified
DEFAULT_STOCK_IDS = ["2330", "2317", "2454", "2308", "2882"]


def _safe_decimal(value) -> Decimal | None:
    """Safely convert a numeric value to Decimal."""
    if value is None:
        return None
    try:
        # Handle NaN from pandas
        if hasattr(value, "__float__"):
            fval = float(value)
            if fval != fval:  # NaN check
                return None
            return Decimal(str(round(fval, 2)))
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _safe_int(value) -> int | None:
    """Safely convert a numeric value to int."""
    if value is None:
        return None
    try:
        fval = float(value)
        if fval != fval:  # NaN check
            return None
        return int(fval)
    except (ValueError, TypeError):
        return None


async def backfill_stock(stock_id: str) -> int:
    """Backfill 6 months of daily prices for a stock using yfinance.

    Args:
        stock_id: Taiwan stock ID (e.g. "2330").

    Returns:
        Number of new records inserted.
    """
    ticker_symbol = f"{stock_id}.TW"
    logger.info("Fetching 6 months of data for %s (%s)...", stock_id, ticker_symbol)

    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="6mo")
    except Exception as exc:
        logger.error("Failed to fetch data for %s: %s", stock_id, exc)
        return 0

    if hist.empty:
        # Some TPEx stocks use .TWO suffix
        ticker_symbol = f"{stock_id}.TWO"
        logger.info("Retrying with TPEx suffix: %s", ticker_symbol)
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="6mo")
        except Exception as exc:
            logger.error("Failed to fetch data for %s: %s", stock_id, exc)
            return 0

    if hist.empty:
        logger.warning("No price data returned for %s", stock_id)
        return 0

    logger.info("Got %d rows for %s", len(hist), stock_id)

    inserted = 0

    async with async_session_factory() as session:
        for idx, row in hist.iterrows():
            # idx is a Timestamp from pandas
            price_date = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])

            # Check if record already exists
            existing = await session.execute(
                select(StockPrice.id).where(
                    StockPrice.stock_id == stock_id,
                    StockPrice.date == price_date,
                ).limit(1)
            )
            if existing.scalar_one_or_none() is not None:
                continue

            open_price = _safe_decimal(row.get("Open"))
            high_price = _safe_decimal(row.get("High"))
            low_price = _safe_decimal(row.get("Low"))
            close_price = _safe_decimal(row.get("Close"))
            volume = _safe_int(row.get("Volume"))

            # Compute change_percent from previous close if available
            change_percent: Decimal | None = None
            # yfinance does not provide change directly; we skip it here

            session.add(
                StockPrice(
                    stock_id=stock_id,
                    date=price_date,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=volume,
                    change_percent=change_percent,
                )
            )
            inserted += 1

        await session.commit()

    logger.info("Inserted %d new price records for %s", inserted, stock_id)
    return inserted


async def main():
    """Entry point: initialize DB and backfill specified stocks."""
    logger.info("Initializing database...")
    await init_db()

    stock_ids = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_STOCK_IDS

    logger.info("Will backfill %d stocks: %s", len(stock_ids), ", ".join(stock_ids))

    total_inserted = 0
    errors = []

    for sid in stock_ids:
        try:
            count = await backfill_stock(sid)
            total_inserted += count
        except Exception as exc:
            logger.error("Error backfilling %s: %s", sid, exc)
            errors.append((sid, str(exc)))

    logger.info("=" * 50)
    logger.info("Backfill complete!")
    logger.info("  Total new records: %d", total_inserted)
    logger.info("  Stocks processed: %d", len(stock_ids))

    if errors:
        logger.warning("  Errors encountered:")
        for sid, err in errors:
            logger.warning("    %s: %s", sid, err)
    else:
        logger.info("  No errors.")


if __name__ == "__main__":
    asyncio.run(main())
