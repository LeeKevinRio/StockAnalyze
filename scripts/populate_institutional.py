"""Populate institutional (三大法人) and margin (融資融券) data via FinMind.

Lights up the 籌碼面 (institutional) dimension/tab. FinMind's free tier works
without a token for a limited number of requests.

Usage:
    cd backend && python ../scripts/populate_institutional.py [stock_ids...]
"""

import asyncio
import logging
import os
import sys
from collections import defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import httpx
from sqlalchemy import select

from app.database import async_session_factory, init_db
from app.models.institutional import InstitutionalTrading, MarginTrading

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT = ["2330", "2317", "2454", "2308", "2882"]
FINMIND = "https://api.finmindtrade.com/api/v4/data"


def _i(v):
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return 0


async def fetch(client, dataset, stock_id, start):
    r = await client.get(FINMIND, params={"dataset": dataset, "data_id": stock_id, "start_date": start})
    r.raise_for_status()
    j = r.json()
    if j.get("msg") != "success":
        logger.warning("FinMind %s %s: %s", dataset, stock_id, j.get("msg"))
        return []
    return j.get("data", [])


async def populate_institutional(client, stock_id, session, start):
    rows = await fetch(client, "TaiwanStockInstitutionalInvestorsBuySell", stock_id, start)
    # Aggregate per date across investor types
    per_date = defaultdict(lambda: {"f_b": 0, "f_s": 0, "t_b": 0, "t_s": 0, "d_b": 0, "d_s": 0})
    for r in rows:
        d = r["date"]
        name = r.get("name", "")
        b, s = _i(r.get("buy")), _i(r.get("sell"))
        if name == "Foreign_Investor":
            per_date[d]["f_b"] += b; per_date[d]["f_s"] += s
        elif name == "Investment_Trust":
            per_date[d]["t_b"] += b; per_date[d]["t_s"] += s
        elif name in ("Dealer_self", "Dealer_Hedging", "Dealer"):
            per_date[d]["d_b"] += b; per_date[d]["d_s"] += s

    have = set((await session.execute(
        select(InstitutionalTrading.date).where(InstitutionalTrading.stock_id == stock_id)
    )).scalars().all())

    n = 0
    for d, v in per_date.items():
        dd = date.fromisoformat(d)
        if dd in have:
            continue
        f_net = v["f_b"] - v["f_s"]; t_net = v["t_b"] - v["t_s"]; d_net = v["d_b"] - v["d_s"]
        session.add(InstitutionalTrading(
            stock_id=stock_id, date=dd,
            foreign_buy=v["f_b"], foreign_sell=v["f_s"], foreign_net=f_net,
            trust_buy=v["t_b"], trust_sell=v["t_s"], trust_net=t_net,
            dealer_buy=v["d_b"], dealer_sell=v["d_s"], dealer_net=d_net,
            total_net=f_net + t_net + d_net,
        ))
        n += 1
    return n


async def populate_margin(client, stock_id, session, start):
    rows = await fetch(client, "TaiwanStockMarginPurchaseShortSale", stock_id, start)
    have = set((await session.execute(
        select(MarginTrading.date).where(MarginTrading.stock_id == stock_id)
    )).scalars().all())
    n = 0
    for r in rows:
        dd = date.fromisoformat(r["date"])
        if dd in have:
            continue
        session.add(MarginTrading(
            stock_id=stock_id, date=dd,
            margin_buy=_i(r.get("MarginPurchaseBuy")),
            margin_sell=_i(r.get("MarginPurchaseSell")),
            margin_balance=_i(r.get("MarginPurchaseTodayBalance")),
            short_buy=_i(r.get("ShortSaleBuy")),
            short_sell=_i(r.get("ShortSaleSell")),
            short_balance=_i(r.get("ShortSaleTodayBalance")),
        ))
        n += 1
    return n


async def main():
    ids = sys.argv[1:] or DEFAULT
    start = (date.today() - timedelta(days=75)).isoformat()
    await init_db()
    async with httpx.AsyncClient(timeout=30) as client:
        async with async_session_factory() as session:
            for sid in ids:
                try:
                    ni = await populate_institutional(client, sid, session, start)
                    nm = await populate_margin(client, sid, session, start)
                    await session.commit()
                    logger.info("%s: +%d institutional days, +%d margin days", sid, ni, nm)
                except Exception:
                    await session.rollback()
                    logger.exception("failed %s", sid)
    logger.info("=== institutional/margin done for %d stocks ===", len(ids))


if __name__ == "__main__":
    asyncio.run(main())
