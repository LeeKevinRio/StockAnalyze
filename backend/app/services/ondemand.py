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

        def _fetch():
            import yfinance as yf
            for suffix in (".TW", ".TWO"):
                t = yf.Ticker(f"{stock_id}{suffix}")
                info = t.info or {}
                if info.get("trailingPE") or info.get("marketCap") or info.get("trailingEps"):
                    return info, t.quarterly_financials, t.quarterly_balance_sheet, t.quarterly_cashflow, t.dividends
            return None

        try:
            res = await asyncio.to_thread(_fetch)
        except Exception:
            logger.exception("yfinance fundamentals fetch failed for %s", stock_id)
            return 0
        if not res:
            return 0
        info, fin, bs, cf, divs = res

        def _row(df, label, col):
            try:
                if df is None or df.empty or label not in df.index or col not in df.columns:
                    return None
                return df.loc[label, col]
            except Exception:
                return None

        db.add(StockFundamental(
            stock_id=stock_id, report_date=date.today(),
            pe_ratio=_dec(info.get("trailingPE")), pb_ratio=_dec(info.get("priceToBook")),
            eps=_dec(info.get("trailingEps")), roe=_dec(info.get("returnOnEquity"), 100),
            roa=_dec(info.get("returnOnAssets"), 100), gross_margin=_dec(info.get("grossMargins"), 100),
            operating_margin=_dec(info.get("operatingMargins"), 100), net_margin=_dec(info.get("profitMargins"), 100),
            revenue=_dec(info.get("totalRevenue")), market_cap=_dec(info.get("marketCap")),
        ))

        cols = list(fin.columns)[:8] if fin is not None and not fin.empty else []
        for col in cols:
            y, q = col.year, (col.month - 1) // 3 + 1
            db.add(FinancialStatement(
                stock_id=stock_id, report_year=y, report_quarter=q,
                revenue=_dec(_row(fin, "Total Revenue", col)), gross_profit=_dec(_row(fin, "Gross Profit", col)),
                operating_income=_dec(_row(fin, "Operating Income", col)), net_income=_dec(_row(fin, "Net Income", col)),
                total_assets=_dec(_row(bs, "Total Assets", col)), total_equity=_dec(_row(bs, "Stockholders Equity", col)),
                operating_cash_flow=_dec(_row(cf, "Operating Cash Flow", col)), free_cash_flow=_dec(_row(cf, "Free Cash Flow", col)),
            ))

        try:
            if divs is not None and not divs.empty:
                by_year: dict[int, float] = {}
                for ts, amt in divs.items():
                    by_year[ts.year] = by_year.get(ts.year, 0.0) + float(amt)
                for y, cash in sorted(by_year.items())[-6:]:
                    db.add(StockDividend(stock_id=stock_id, year=y, cash_dividend=_dec(cash),
                                         dividend_yield=_dec(info.get("dividendYield"))))
        except Exception:
            pass

        await db.commit()
        logger.info("On-demand fundamentals backfilled for %s", stock_id)
        return 1


# ---------------------------------------------------------------------------
# Institutional + margin (FinMind)
# ---------------------------------------------------------------------------

async def ensure_institutional(stock_id: str, db: AsyncSession) -> int:
    exists = (
        await db.execute(select(InstitutionalTrading.id).where(InstitutionalTrading.stock_id == stock_id).limit(1))
    ).scalar_one_or_none()
    if exists is not None:
        return 0
    lock = _inst_locks.setdefault(stock_id, asyncio.Lock())
    async with lock:
        exists = (
            await db.execute(select(InstitutionalTrading.id).where(InstitutionalTrading.stock_id == stock_id).limit(1))
        ).scalar_one_or_none()
        if exists is not None:
            return 0

        start = (date.today() - timedelta(days=75)).isoformat()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                inst = await _finmind(client, "TaiwanStockInstitutionalInvestorsBuySell", stock_id, start)
                margin = await _finmind(client, "TaiwanStockMarginPurchaseShortSale", stock_id, start)
        except Exception:
            logger.exception("FinMind fetch failed for %s", stock_id)
            return 0

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
            f, t, dl = v["f_b"] - v["f_s"], v["t_b"] - v["t_s"], v["d_b"] - v["d_s"]
            db.add(InstitutionalTrading(
                stock_id=stock_id, date=date.fromisoformat(d),
                foreign_buy=v["f_b"], foreign_sell=v["f_s"], foreign_net=f,
                trust_buy=v["t_b"], trust_sell=v["t_s"], trust_net=t,
                dealer_buy=v["d_b"], dealer_sell=v["d_s"], dealer_net=dl, total_net=f + t + dl,
            )); n += 1
        for r in margin:
            db.add(MarginTrading(
                stock_id=stock_id, date=date.fromisoformat(r["date"]),
                margin_buy=_i(r.get("MarginPurchaseBuy")), margin_sell=_i(r.get("MarginPurchaseSell")),
                margin_balance=_i(r.get("MarginPurchaseTodayBalance")),
                short_buy=_i(r.get("ShortSaleBuy")), short_sell=_i(r.get("ShortSaleSell")),
                short_balance=_i(r.get("ShortSaleTodayBalance")),
            ))
        await db.commit()
        logger.info("On-demand institutional backfilled %d days for %s", n, stock_id)
        return n


async def _finmind(client, dataset, stock_id, start):
    r = await client.get(FINMIND, params={"dataset": dataset, "data_id": stock_id, "start_date": start})
    r.raise_for_status()
    j = r.json()
    return j.get("data", []) if j.get("msg") == "success" else []
