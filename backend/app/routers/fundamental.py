"""Fundamental analysis API endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stock import Stock
from app.schemas.fundamental import (
    DividendItem,
    DividendsResponse,
    FinancialStatementItem,
    FinancialsResponse,
    FundamentalDataResponse,
    PeerComparisonItem,
    PeersResponse,
    RevenueTrendItem,
    RevenueTrendResponse,
)
from app.services.fundamental_service import fundamental_service

router = APIRouter()


async def _get_stock_or_404(stock_id: str, db: AsyncSession) -> Stock:
    """Retrieve stock or raise 404."""
    result = await db.execute(select(Stock).where(Stock.stock_id == stock_id))
    stock = result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {stock_id} not found")
    return stock


@router.get("/{stock_id}", response_model=FundamentalDataResponse)
async def get_fundamental_analysis(
    stock_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get latest fundamental data with full analysis and scoring."""
    stock = await _get_stock_or_404(stock_id, db)

    fundamentals = await fundamental_service.get_fundamentals(stock_id, db)
    statements = await fundamental_service.get_financial_statements(stock_id, db, quarters=8)
    dividends = await fundamental_service.get_dividends(stock_id, db, years=5)
    peers = await fundamental_service.get_peer_stocks(stock_id, db)

    analysis = fundamental_service.analyze(fundamentals, statements, dividends, peers)
    score = fundamental_service.calculate_score(analysis)
    summary = fundamental_service.generate_summary(score, analysis)

    return FundamentalDataResponse(
        stock_id=stock_id,
        stock_name=stock.name,
        report_date=fundamentals.get("report_date"),
        pe_ratio=analysis.pe_ratio,
        pb_ratio=analysis.pb_ratio,
        ps_ratio=fundamentals.get("ps_ratio"),
        market_cap=analysis.market_cap,
        eps=analysis.eps,
        roe=analysis.roe,
        roa=analysis.roa,
        gross_margin=analysis.gross_margin,
        operating_margin=analysis.operating_margin,
        net_margin=analysis.net_margin,
        eps_growth_qoq=analysis.eps_growth_qoq,
        eps_growth_yoy=analysis.eps_growth_yoy,
        revenue_growth_mom=analysis.revenue_growth_mom,
        revenue_growth_yoy=analysis.revenue_growth_yoy,
        dividend_yield=analysis.dividend_yield,
        industry=stock.industry,
        industry_pe_avg=analysis.industry_pe_avg,
        valuation_assessment=analysis.valuation_assessment,
        growth_assessment=analysis.growth_assessment,
        profitability_assessment=analysis.profitability_assessment,
        score=score,
        summary=summary,
    )


@router.get("/{stock_id}/revenue-trend", response_model=RevenueTrendResponse)
async def get_revenue_trend(
    stock_id: str,
    quarters: int = Query(12, ge=4, le=24, description="Number of quarters"),
    db: AsyncSession = Depends(get_db),
):
    """Get monthly revenue trend derived from quarterly statements.

    Returns quarterly revenue data that can be visualized as a trend chart.
    """
    stock = await _get_stock_or_404(stock_id, db)
    statements = await fundamental_service.get_financial_statements(stock_id, db, quarters=quarters)

    data = []
    for i, stmt in enumerate(statements):
        mom_growth = None
        yoy_growth = None

        # MoM (quarter-over-quarter) growth
        if i + 1 < len(statements) and stmt.get("revenue") and statements[i + 1].get("revenue"):
            prev_rev = statements[i + 1]["revenue"]
            if prev_rev != 0:
                mom_growth = (stmt["revenue"] - prev_rev) / abs(prev_rev) * 100

        # YoY growth (4 quarters back)
        if i + 4 < len(statements) and stmt.get("revenue") and statements[i + 4].get("revenue"):
            prev_rev = statements[i + 4]["revenue"]
            if prev_rev != 0:
                yoy_growth = (stmt["revenue"] - prev_rev) / abs(prev_rev) * 100

        # Use quarter as a proxy for month (Q1=3, Q2=6, Q3=9, Q4=12)
        quarter_month = stmt["quarter"] * 3

        data.append(
            RevenueTrendItem(
                year=stmt["year"],
                month=quarter_month,
                revenue=stmt.get("revenue"),
                revenue_yoy_growth=round(yoy_growth, 2) if yoy_growth is not None else None,
                revenue_mom_growth=round(mom_growth, 2) if mom_growth is not None else None,
            )
        )

    return RevenueTrendResponse(
        stock_id=stock_id,
        stock_name=stock.name,
        data=data,
    )


@router.get("/{stock_id}/financials", response_model=FinancialsResponse)
async def get_financial_statements(
    stock_id: str,
    quarters: int = Query(8, ge=1, le=20, description="Number of quarters"),
    db: AsyncSession = Depends(get_db),
):
    """Get quarterly financial statements."""
    stock = await _get_stock_or_404(stock_id, db)
    statements = await fundamental_service.get_financial_statements(stock_id, db, quarters=quarters)

    items = []
    for stmt in statements:
        total_equity = stmt.get("total_equity")
        net_income = stmt.get("net_income")
        roe = None
        if total_equity and net_income and total_equity != 0:
            roe = round(net_income / total_equity * 100, 2)

        revenue = stmt.get("revenue")
        eps = None  # Would need shares outstanding for true EPS

        items.append(
            FinancialStatementItem(
                year=stmt["year"],
                quarter=stmt["quarter"],
                revenue=stmt.get("revenue"),
                gross_profit=stmt.get("gross_profit"),
                operating_income=stmt.get("operating_income"),
                net_income=stmt.get("net_income"),
                eps=eps,
                gross_margin=round(stmt["gross_margin"], 2) if stmt.get("gross_margin") is not None else None,
                operating_margin=round(stmt["operating_margin"], 2) if stmt.get("operating_margin") is not None else None,
                net_margin=round(stmt["net_margin"], 2) if stmt.get("net_margin") is not None else None,
                roe=roe,
                total_assets=stmt.get("total_assets"),
                total_equity=total_equity,
                operating_cash_flow=stmt.get("operating_cash_flow"),
                free_cash_flow=stmt.get("free_cash_flow"),
            )
        )

    return FinancialsResponse(
        stock_id=stock_id,
        stock_name=stock.name,
        statements=items,
    )


@router.get("/{stock_id}/dividends", response_model=DividendsResponse)
async def get_dividend_history(
    stock_id: str,
    years: int = Query(5, ge=1, le=20, description="Number of years"),
    db: AsyncSession = Depends(get_db),
):
    """Get dividend history."""
    stock = await _get_stock_or_404(stock_id, db)
    dividends = await fundamental_service.get_dividends(stock_id, db, years=years)

    items = []
    yields = []
    for d in dividends:
        cash = d.get("cash_dividend") or 0
        stock_div = d.get("stock_dividend") or 0
        total = cash + stock_div
        dy = d.get("dividend_yield")
        if dy is not None:
            yields.append(dy)

        ex_date = None
        if d.get("ex_dividend_date"):
            try:
                ex_date = date.fromisoformat(d["ex_dividend_date"])
            except (ValueError, TypeError):
                ex_date = None

        items.append(
            DividendItem(
                year=d["year"],
                cash_dividend=cash if cash else None,
                stock_dividend=stock_div if stock_div else None,
                total_dividend=total if total else None,
                dividend_yield=dy,
                ex_dividend_date=ex_date,
            )
        )

    avg_yield = round(sum(yields) / len(yields), 2) if yields else None

    return DividendsResponse(
        stock_id=stock_id,
        stock_name=stock.name,
        dividends=items,
        avg_yield_5y=avg_yield,
    )


@router.get("/{stock_id}/peers", response_model=PeersResponse)
async def get_peer_comparison(
    stock_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get peer comparison within the same industry."""
    stock = await _get_stock_or_404(stock_id, db)
    peers_data = await fundamental_service.get_peer_stocks(stock_id, db)

    peers = [
        PeerComparisonItem(
            stock_id=p["stock_id"],
            stock_name=p["stock_name"],
            pe_ratio=p.get("pe_ratio"),
            pb_ratio=p.get("pb_ratio"),
            roe=p.get("roe"),
            eps=p.get("eps"),
            gross_margin=p.get("gross_margin"),
            dividend_yield=p.get("dividend_yield"),
            market_cap=p.get("market_cap"),
        )
        for p in peers_data
    ]

    # Calculate industry averages
    pe_values = [p.pe_ratio for p in peers if p.pe_ratio and p.pe_ratio > 0]
    pb_values = [p.pb_ratio for p in peers if p.pb_ratio and p.pb_ratio > 0]
    roe_values = [p.roe for p in peers if p.roe is not None]

    return PeersResponse(
        stock_id=stock_id,
        stock_name=stock.name,
        industry=stock.industry,
        peers=peers,
        industry_pe_avg=round(sum(pe_values) / len(pe_values), 2) if pe_values else None,
        industry_pb_avg=round(sum(pb_values) / len(pb_values), 2) if pb_values else None,
        industry_roe_avg=round(sum(roe_values) / len(roe_values), 2) if roe_values else None,
    )
