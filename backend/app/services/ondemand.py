"""On-demand data backfill — fetch a stock's data the first time it is viewed.

Keeps the app usable for any stock without bulk-seeding all 1000+ symbols.
Each ``ensure_*`` function is a no-op if the data already exists, and uses a
per-stock lock so concurrent requests don't double-fetch.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fundamental import FinancialStatement, StockDividend, StockFundamental
from app.models.institutional import InstitutionalTrading, MarginTrading

logger = logging.getLogger(__name__)

_fund_locks: dict[str, asyncio.Lock] = {}
_inst_locks: dict[str, asyncio.Lock] = {}

FINMIND = "https://api.finmindtrade.com/api/v4/data"


def _dec(v, scale=1.0):
    try:
        if v is None:
            return None
        f = float(v) * scale
        if f != f:
            return None
        return Decimal(str(round(f, 2)))
    except (TypeError, ValueError, InvalidOperation):
        return None


def _i(v):
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------------------------
# Fundamentals (yfinance)
# ---------------------------------------------------------------------------

async def ensure_fundamentals(stock_id: str, db: AsyncSession) -> int:
    """Backfill fundamentals from FinMind (PER + financial statements).

    Uses FinMind rather than yfinance because Yahoo blocks datacenter IPs.
    """
    exists = (
        await db.execute(select(StockFundamental.id).where(StockFundamental.stock_id == stock_id).limit(1))
    ).scalar_one_or_none()
    if exists is not None:
        return 0
    lock = _fund_locks.setdefault(stock_id, asyncio.Lock())
    async with lock:
        exists = (
            await db.execute(select(StockFundamental.id).where(StockFundamental.stock_id == stock_id).limit(1))
        ).scalar_one_or_none()
        if exists is not None:
            return 0

        per_start = (date.today() - timedelta(days=400)).isoformat()
        fs_start = (date.today() - timedelta(days=800)).isoformat()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                per = await _finmind(client, "TaiwanStockPER", stock_id, per_start)
                fs = await _finmind(client, "TaiwanStockFinancialStatements", stock_id, fs_start)
        except Exception:
            logger.exception("FinMind fundamentals fetch failed for %s", stock_id)
            return 0

        if not per and not fs:
            return 0

        # Latest valuation from PER dataset.
        latest_per = per[-1] if per else {}

        # Pivot financial statements: {date: {type: value}}.
        by_date: dict[str, dict] = defaultdict(dict)
        for r in fs:
            by_date[r["date"]][r.get("type")] = r.get("value")
        dates_sorted = sorted(by_date.keys())

        def g(d, *types):
            for t in types:
                v = by_date[d].get(t)
                if v is not None:
                    return v
            return None

        # Quarterly statement rows (last 8).
        for d in dates_sorted[-8:]:
            dt = date.fromisoformat(d)
            db.add(FinancialStatement(
                stock_id=stock_id, report_year=dt.year, report_quarter=(dt.month - 1) // 3 + 1,
                revenue=_dec(g(d, "Revenue")),
                gross_profit=_dec(g(d, "GrossProfit")),
                operating_income=_dec(g(d, "OperatingIncome", "OperatingProfit")),
                net_income=_dec(g(d, "IncomeAfterTax", "IncomeAfterTaxes", "TotalConsolidatedProfitForThePeriod")),
            ))

        # Valuation snapshot from the latest quarter + PER.
        latest_d = dates_sorted[-1] if dates_sorted else None
        rev = g(latest_d, "Revenue") if latest_d else None
        ni = g(latest_d, "IncomeAfterTax", "IncomeAfterTaxes") if latest_d else None
        gp = g(latest_d, "GrossProfit") if latest_d else None
        oi = g(latest_d, "OperatingIncome", "OperatingProfit") if latest_d else None
        # Trailing EPS = sum of last 4 quarters' EPS if available.
        eps_vals = [by_date[d].get("EPS") for d in dates_sorted[-4:] if by_date[d].get("EPS") is not None]
        eps_ttm = sum(eps_vals) if eps_vals else None

        def margin(num):
            try:
                return _dec(float(num) / float(rev) * 100) if num and rev else None
            except (TypeError, ValueError, ZeroDivisionError):
                return None

        db.add(StockFundamental(
            stock_id=stock_id, report_date=date.today(),
            pe_ratio=_dec(latest_per.get("PER")), pb_ratio=_dec(latest_per.get("PBR")),
            eps=_dec(eps_ttm), revenue=_dec(rev),
            gross_margin=margin(gp), operating_margin=margin(oi), net_margin=margin(ni),
        ))

        await db.commit()
        logger.info("On-demand fundamentals backfilled for %s (FinMind)", stock_id)
        return 1


# ---------------------------------------------------------------------------
# Institutional + margin (FinMind)
# ---------------------------------------------------------------------------

async def ensure_institutional(stock_id: str, db: AsyncSession) -> int:
    """Keep institutional + margin data fresh (incremental top-up to last trading day)."""
    from app.utils.date_utils import get_last_trading_day

    target = get_last_trading_day()
    max_date = (
        await db.execute(
            select(InstitutionalTrading.date).where(InstitutionalTrading.stock_id == stock_id)
            .order_by(InstitutionalTrading.date.desc()).limit(1)
        )
    ).scalar_one_or_none()
    if max_date is not None and max_date >= target:
        return 0
    lock = _inst_locks.setdefault(stock_id, asyncio.Lock())
    async with lock:
        max_date = (
            await db.execute(
                select(InstitutionalTrading.date).where(InstitutionalTrading.stock_id == stock_id)
                .order_by(InstitutionalTrading.date.desc()).limit(1)
            )
        ).scalar_one_or_none()
        if max_date is not None and max_date >= target:
            return 0

        start_date = (max_date - timedelta(days=5)) if max_date else (date.today() - timedelta(days=75))
        start = start_date.isoformat()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                inst = await _finmind(client, "TaiwanStockInstitutionalInvestorsBuySell", stock_id, start)
                margin = await _finmind(client, "TaiwanStockMarginPurchaseShortSale", stock_id, start)
        except Exception:
            logger.exception("FinMind fetch failed for %s", stock_id)
            return 0

        inst_have = set((await db.execute(
            select(InstitutionalTrading.date).where(
                InstitutionalTrading.stock_id == stock_id, InstitutionalTrading.date >= start_date)
        )).scalars().all())
        margin_have = set((await db.execute(
            select(MarginTrading.date).where(
                MarginTrading.stock_id == stock_id, MarginTrading.date >= start_date)
        )).scalars().all())

        per_date = defaultdict(lambda: {"f_b": 0, "f_s": 0, "t_b": 0, "t_s": 0, "d_b": 0, "d_s": 0})
        for r in inst:
            d, name = r["date"], r.get("name", "")
            b, s = _i(r.get("buy")), _i(r.get("sell"))
            if name == "Foreign_Investor":
                per_date[d]["f_b"] += b; per_date[d]["f_s"] += s
            elif name == "Investment_Trust":
                per_date[d]["t_b"] += b; per_date[d]["t_s"] += s
            elif name in ("Dealer_self", "Dealer_Hedging", "Dealer"):
                per_date[d]["d_b"] += b; per_date[d]["d_s"] += s
        n = 0
        for d, v in per_date.items():
            dd = date.fromisoformat(d)
            if dd in inst_have:
                continue
            f, t, dl = v["f_b"] - v["f_s"], v["t_b"] - v["t_s"], v["d_b"] - v["d_s"]
            db.add(InstitutionalTrading(
                stock_id=stock_id, date=dd,
                foreign_buy=v["f_b"], foreign_sell=v["f_s"], foreign_net=f,
                trust_buy=v["t_b"], trust_sell=v["t_s"], trust_net=t,
                dealer_buy=v["d_b"], dealer_sell=v["d_s"], dealer_net=dl, total_net=f + t + dl,
            )); n += 1
        for r in margin:
            dd = date.fromisoformat(r["date"])
            if dd in margin_have:
                continue
            db.add(MarginTrading(
                stock_id=stock_id, date=dd,
                margin_buy=_i(r.get("MarginPurchaseBuy")), margin_sell=_i(r.get("MarginPurchaseSell")),
                margin_balance=_i(r.get("MarginPurchaseTodayBalance")),
                short_buy=_i(r.get("ShortSaleBuy")), short_sell=_i(r.get("ShortSaleSell")),
                short_balance=_i(r.get("ShortSaleTodayBalance")),
            ))
        await db.commit()
        logger.info("Institutional for %s: +%d days (up to %s)", stock_id, n, target)
        return n


async def _finmind(client, dataset, stock_id, start):
    r = await client.get(FINMIND, params={"dataset": dataset, "data_id": stock_id, "start_date": start})
    r.raise_for_status()
    j = r.json()
    return j.get("data", []) if j.get("msg") == "success" else []
