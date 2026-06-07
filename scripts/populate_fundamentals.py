"""Populate fundamentals, quarterly financial statements and dividends via yfinance.

Lights up the 基本面 (fundamental) dimension/tab for the given stocks.

Usage:
    cd backend && python ../scripts/populate_fundamentals.py [stock_ids...]
"""

import asyncio
import logging
import os
import sys
from datetime import date
from decimal import Decimal, InvalidOperation

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import yfinance as yf
from sqlalchemy import select

from app.database import async_session_factory, init_db
from app.models.fundamental import StockFundamental, FinancialStatement, StockDividend

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT = ["2330", "2317", "2454", "2308", "2882"]


def D(v, scale=1.0):
    """Safe Decimal conversion (returns None on bad/NaN input)."""
    try:
        if v is None:
            return None
        f = float(v) * scale
        if f != f:  # NaN
            return None
        return Decimal(str(round(f, 2)))
    except (TypeError, ValueError, InvalidOperation):
        return None


def row(df, label, col):
    try:
        if df is None or df.empty or label not in df.index or col not in df.columns:
            return None
        return df.loc[label, col]
    except Exception:
        return None


async def populate(stock_id: str, session) -> None:
    t = yf.Ticker(f"{stock_id}.TW")
    info = t.info or {}

    # --- Valuation snapshot ---
    today = date.today()
    existing = (
        await session.execute(
            select(StockFundamental).where(
                StockFundamental.stock_id == stock_id,
                StockFundamental.report_date == today,
            )
        )
    ).scalar_one_or_none()
    fund = existing or StockFundamental(stock_id=stock_id, report_date=today)
    fund.pe_ratio = D(info.get("trailingPE"))
    fund.pb_ratio = D(info.get("priceToBook"))
    fund.eps = D(info.get("trailingEps"))
    fund.roe = D(info.get("returnOnEquity"), 100)
    fund.roa = D(info.get("returnOnAssets"), 100)
    fund.gross_margin = D(info.get("grossMargins"), 100)
    fund.operating_margin = D(info.get("operatingMargins"), 100)
    fund.net_margin = D(info.get("profitMargins"), 100)
    fund.revenue = D(info.get("totalRevenue"))
    fund.market_cap = D(info.get("marketCap"))
    if not existing:
        session.add(fund)

    # --- Quarterly financial statements (last ~8 quarters) ---
    fin = t.quarterly_financials
    bs = t.quarterly_balance_sheet
    cf = t.quarterly_cashflow
    cols = list(fin.columns)[:8] if fin is not None and not fin.empty else []
    have = set(
        (await session.execute(
            select(FinancialStatement.report_year, FinancialStatement.report_quarter)
            .where(FinancialStatement.stock_id == stock_id)
        )).all()
    )
    fs_count = 0
    for col in cols:
        y = col.year
        q = (col.month - 1) // 3 + 1
        if (y, q) in have:
            continue
        session.add(FinancialStatement(
            stock_id=stock_id, report_year=y, report_quarter=q,
            revenue=D(row(fin, "Total Revenue", col)),
            gross_profit=D(row(fin, "Gross Profit", col)),
            operating_income=D(row(fin, "Operating Income", col)),
            net_income=D(row(fin, "Net Income", col)),
            total_assets=D(row(bs, "Total Assets", col)),
            total_equity=D(row(bs, "Stockholders Equity", col)),
            operating_cash_flow=D(row(cf, "Operating Cash Flow", col)),
            free_cash_flow=D(row(cf, "Free Cash Flow", col)),
        ))
        fs_count += 1

    # --- Dividends (aggregate cash dividend per year) ---
    div_count = 0
    try:
        divs = t.dividends
        if divs is not None and not divs.empty:
            by_year: dict[int, float] = {}
            for ts, amt in divs.items():
                by_year[ts.year] = by_year.get(ts.year, 0.0) + float(amt)
            have_years = set(
                (await session.execute(
                    select(StockDividend.year).where(StockDividend.stock_id == stock_id)
                )).scalars().all()
            )
            for y, cash in sorted(by_year.items())[-6:]:
                if y in have_years:
                    continue
                session.add(StockDividend(
                    stock_id=stock_id, year=y,
                    cash_dividend=D(cash),
                    dividend_yield=D(info.get("dividendYield")),
                ))
                div_count += 1
    except Exception as e:
        logger.warning("dividends failed for %s: %s", stock_id, e)

    await session.commit()
    logger.info("%s: valuation OK, +%d statements, +%d dividend years", stock_id, fs_count, div_count)


async def main():
    ids = sys.argv[1:] or DEFAULT
    await init_db()
    async with async_session_factory() as session:
        for sid in ids:
            try:
                await populate(sid, session)
            except Exception:
                await session.rollback()
                logger.exception("failed %s", sid)
    logger.info("=== fundamentals done for %d stocks ===", len(ids))


if __name__ == "__main__":
    asyncio.run(main())
