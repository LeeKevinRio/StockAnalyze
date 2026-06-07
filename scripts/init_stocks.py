"""
Initialize the stocks table with all TWSE/TPEx listed companies.
Fetches from TWSE Open API and inserts into database.

Usage:
    cd backend && python -m scripts.init_stocks
    or:
    python scripts/init_stocks.py
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import httpx
from sqlalchemy import select
from app.database import async_session_factory, init_db
from app.models.stock import Stock


TWSE_STOCK_LIST_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TPEX_STOCK_LIST_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_O"


async def fetch_stock_list(url: str, market: str) -> list[dict]:
    """Fetch stock list from TWSE/TPEx API."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    stocks = []
    for item in data:
        stock_id = item.get("公司代號", "").strip()
        name = item.get("公司簡稱", "").strip()
        industry = item.get("產業類別", "").strip()

        if not stock_id or not name:
            continue

        # Only include stocks with 4-digit IDs (skip ETFs, warrants, etc. for now)
        if not stock_id.isdigit() or len(stock_id) != 4:
            continue

        stocks.append({
            "stock_id": stock_id,
            "name": name,
            "industry": industry or None,
            "market": market,
        })

    return stocks


async def main():
    print("Initializing database tables...")
    await init_db()

    print("\nFetching TWSE listed stocks...")
    twse_stocks = await fetch_stock_list(TWSE_STOCK_LIST_URL, "TWSE")
    print(f"  Found {len(twse_stocks)} TWSE stocks")

    print("Fetching TPEx listed stocks...")
    try:
        tpex_stocks = await fetch_stock_list(TPEX_STOCK_LIST_URL, "TPEx")
        print(f"  Found {len(tpex_stocks)} TPEx stocks")
    except Exception as e:
        tpex_stocks = []
        print(f"  WARNING: TPEx fetch failed ({e}); continuing with TWSE stocks only")

    all_stocks = twse_stocks + tpex_stocks
    print(f"\nTotal: {len(all_stocks)} stocks")

    print("\nInserting into database...")
    async with async_session_factory() as session:
        inserted = 0
        updated = 0

        for stock_data in all_stocks:
            existing = await session.execute(
                select(Stock).where(Stock.stock_id == stock_data["stock_id"])
            )
            existing_stock = existing.scalar_one_or_none()

            if existing_stock:
                existing_stock.name = stock_data["name"]
                existing_stock.industry = stock_data["industry"]
                existing_stock.market = stock_data["market"]
                updated += 1
            else:
                session.add(Stock(**stock_data))
                inserted += 1

        await session.commit()
        print(f"  Inserted: {inserted}, Updated: {updated}")

    print("\nDone! Stock list initialized successfully.")

    # Print some samples
    async with async_session_factory() as session:
        result = await session.execute(select(Stock).limit(5))
        samples = result.scalars().all()
        print("\nSample stocks:")
        for s in samples:
            print(f"  {s.stock_id} {s.name} ({s.industry}) - {s.market}")


if __name__ == "__main__":
    asyncio.run(main())
