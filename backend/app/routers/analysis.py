"""Analysis-related API endpoints."""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.analysis import AnalysisReport
from app.models.stock import Stock, StockPrice
from app.schemas.analysis import AnalysisReportResponse, AnalysisScoresResponse, DimensionScore

logger = logging.getLogger(__name__)

router = APIRouter()

# Curated universe scanned by the AI screener — liquid large/mid caps across
# sectors. Kept small so a refresh stays within request-time + free-tier limits.
SCREENER_UNIVERSE = [
    "2330", "2317", "2454", "2308", "2303", "2412", "2882", "2881",
    "2891", "2603", "2609", "1301", "1303", "2002", "3008", "2379",
    "3037", "2357", "2382", "6505",
]


def _signal_from_score(score: float) -> str:
    if score >= 60:
        return "strong_buy"
    elif score >= 20:
        return "buy"
    elif score >= -20:
        return "neutral"
    elif score >= -60:
        return "sell"
    return "strong_sell"


def _dim_signal(score: float) -> str:
    if score >= 20:
        return "bullish"
    elif score >= -20:
        return "neutral"
    return "bearish"


async def _latest_quote(stock_id: str, db: AsyncSession) -> dict:
    """Latest close + day change for a stock, read-only from stored prices."""
    prices = (
        await db.execute(
            select(StockPrice)
            .where(StockPrice.stock_id == stock_id)
            .order_by(StockPrice.date.desc())
            .limit(2)
        )
    ).scalars().all()
    if not prices:
        return {"close": None, "change_percent": None}
    latest = float(prices[0].close) if prices[0].close is not None else None
    prev = float(prices[1].close) if len(prices) > 1 and prices[1].close is not None else latest
    change_pct = ((latest - prev) / prev * 100) if (latest is not None and prev) else None
    return {
        "close": round(latest, 2) if latest is not None else None,
        "change_percent": round(change_pct, 2) if change_pct is not None else None,
    }


async def _report_to_pick(report: AnalysisReport, db: AsyncSession) -> dict:
    """Shape a stored report into a screener row (scores + name + quote)."""
    stock = (
        await db.execute(select(Stock).where(Stock.stock_id == report.stock_id))
    ).scalar_one_or_none()
    quote = await _latest_quote(report.stock_id, db)
    return {
        "stock_id": report.stock_id,
        "name": stock.name if stock else report.stock_id,
        "industry": stock.industry if stock else None,
        "overall_score": float(report.overall_score or 0),
        "overall_signal": report.overall_signal or "neutral",
        "confidence": float(report.confidence or 0),
        "scores": {
            "news": float(report.news_score or 0),
            "fundamental": float(report.fundamental_score or 0),
            "technical": float(report.technical_score or 0),
            "institutional": float(report.institutional_score or 0),
            "macro": float(report.macro_score or 0),
        },
        "target_price": float(report.target_price) if report.target_price is not None else None,
        "report_date": report.report_date.isoformat() if report.report_date else None,
        "close": quote["close"],
        "change_percent": quote["change_percent"],
    }


def _rank(picks: list[dict], signal: str | None, sort: str, limit: int) -> list[dict]:
    """Filter by signal and sort screener rows."""
    rows = picks
    if signal and signal != "all":
        rows = [p for p in rows if p["overall_signal"] == signal]
    keymap = {
        "overall": lambda p: p["overall_score"],
        "technical": lambda p: p["scores"]["technical"],
        "fundamental": lambda p: p["scores"]["fundamental"],
        "institutional": lambda p: p["scores"]["institutional"],
        "confidence": lambda p: p["confidence"],
        "change": lambda p: p["change_percent"] if p["change_percent"] is not None else -999,
    }
    key = keymap.get(sort, keymap["overall"])
    rows = sorted(rows, key=key, reverse=True)
    return rows[:limit]


@router.get("/screener")
async def screen_stocks(
    limit: int = Query(20, ge=1, le=50),
    signal: str | None = Query(None, description="Filter: strong_buy/buy/neutral/sell/strong_sell/all"),
    sort: str = Query("overall", description="overall/technical/fundamental/institutional/confidence/change"),
    db: AsyncSession = Depends(get_db),
):
    """AI 選股 — rank every stock that already has an analysis report.

    Read-only and fast. Returns [] when nothing has been analysed yet; the
    client can then call POST /screener/refresh to populate the universe.
    """
    # Latest report per stock (highest report_date wins).
    reports = (
        await db.execute(
            select(AnalysisReport).order_by(
                AnalysisReport.stock_id, AnalysisReport.report_date.desc()
            )
        )
    ).scalars().all()

    seen: set[str] = set()
    latest: list[AnalysisReport] = []
    for r in reports:
        if r.stock_id in seen:
            continue
        seen.add(r.stock_id)
        latest.append(r)

    picks = [await _report_to_pick(r, db) for r in latest]
    return _rank(picks, signal, sort, limit)


async def _refresh_news_if_stale(stock_id: str, db: AsyncSession) -> None:
    """Top up a stock's news when the last fetch is older than 6 h.

    Keeps 消息面 alive for the daily scan: without this, news only arrived
    when someone happened to open the stock page.
    """
    from sqlalchemy import func as safunc

    from app.models.news import StockNews
    from app.services.news_service import fetch_and_store_news

    last = (
        await db.execute(
            select(safunc.max(StockNews.fetched_at)).where(StockNews.stock_id == stock_id)
        )
    ).scalar_one_or_none()
    if last is not None and (datetime.now(timezone.utc) - last) < timedelta(hours=6):
        return
    stock = (
        await db.execute(select(Stock).where(Stock.stock_id == stock_id))
    ).scalar_one_or_none()
    if stock is None:
        return
    try:
        await fetch_and_store_news(stock_id, stock.name, db)
    except Exception:
        logger.warning("News refresh failed for %s", stock_id, exc_info=True)


async def _compute_pick(stock_id: str, db: AsyncSession) -> dict | None:
    """Ensure data, run the (non-LLM) engine, persist scores, return a row."""
    from app.services.analysis_engine import analysis_engine
    from app.services.ondemand import ensure_fundamentals, ensure_institutional
    from app.services.stock_service import ensure_price_history

    # Don't clobber a richer AI report generated today; only (re)compute when the
    # latest report is missing, stale, or itself a lightweight screener pass.
    existing = (
        await db.execute(
            select(AnalysisReport)
            .where(AnalysisReport.stock_id == stock_id)
            .order_by(AnalysisReport.report_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if (
        existing is not None
        and existing.report_date == date.today()
        and existing.ai_provider not in (None, "screener")
    ):
        return None

    try:
        await ensure_price_history(stock_id, db)
        await ensure_fundamentals(stock_id, db)
        await ensure_institutional(stock_id, db)
        await _refresh_news_if_stale(stock_id, db)
        result = await analysis_engine.analyze(stock_id, db)
    except Exception:
        logger.exception("Screener compute failed for %s", stock_id)
        return None

    # Persist dimension scores without clobbering a richer AI report: only write
    # a lightweight markdown when no report exists for today yet.
    markdown = _synthesize_markdown(result)
    await analysis_engine.save_report(
        stock_id=stock_id,
        result=result,
        ai_report=markdown,
        ai_provider="screener",
        db=db,
    )
    return None


def _synthesize_markdown(result) -> str:
    """Build a short non-LLM markdown summary from dimension details."""
    lines = [f"## {result.stock_name} 快速評分", ""]
    label = {
        "news": "消息面", "fundamental": "基本面", "technical": "技術面",
        "institutional": "籌碼面", "macro": "總經面",
    }
    for key, name in label.items():
        detail = (result.dimension_details or {}).get(key, {})
        summary = detail.get("summary", "")
        lines.append(f"- **{name}** ({result.scores.get(key, 0):+.0f})：{summary}")
    lines.append("")
    lines.append(f"> 綜合評分 {result.overall_score:+.0f}（{result.overall_signal}），由 AI 選股快速掃描產生。如需完整 AI 報告請於個股頁點「產生 AI 分析」。")
    return "\n".join(lines)


@router.post("/screener/refresh")
async def refresh_screener(
    limit: int = Query(20, ge=1, le=50),
    signal: str | None = Query(None),
    sort: str = Query("overall"),
    llm_top: int = Query(0, ge=0, le=10, description="Generate full LLM reports for the top N stocks"),
    db: AsyncSession = Depends(get_db),
):
    """Scan the curated universe: backfill data, score each stock, persist.

    Also tops up per-stock news (staleness-gated) and market-wide social
    sentiment so 消息面 has signal. With ``llm_top`` > 0, generates full LLM
    reports for the N highest-scoring stocks (skipping any that already got
    a real LLM report today — protects the free-tier quota).

    Slower than GET (does on-demand fetches), but only the first run per stock
    is heavy — afterwards the data is cached. Returns the freshly ranked list.
    """
    # Sequential to stay gentle on FinMind's free tier and the DB session.
    # Commit per stock so a mid-request timeout keeps the progress so far.
    for sid in SCREENER_UNIVERSE:
        await _compute_pick(sid, db)
        await db.commit()

    # Market-wide social sentiment (PTT) — one scrape, deduped by URL.
    try:
        from app.services.sentiment_service import fetch_and_analyze_social

        await fetch_and_analyze_social(db)
        await db.commit()
    except Exception:
        logger.warning("Social sentiment fetch failed", exc_info=True)
        await db.rollback()

    if llm_top:
        await _generate_llm_reports_for_top(llm_top, db)

    return await screen_stocks(limit=limit, signal=signal, sort=sort, db=db)


# Providers that mean "no real LLM report yet" — worth upgrading.
_NON_LLM_PROVIDERS = (None, "", "screener", "fallback", "unknown")


async def _generate_llm_reports_for_top(n: int, db: AsyncSession) -> None:
    """Generate full LLM reports for today's top-N stocks by overall score."""
    from app.services.analysis_engine import analysis_engine
    from app.services.report_generator import report_generator

    reports = (
        await db.execute(
            select(AnalysisReport)
            .where(AnalysisReport.report_date == date.today())
            .order_by(AnalysisReport.overall_score.desc())
            .limit(n)
        )
    ).scalars().all()

    for rep in reports:
        if rep.ai_provider not in _NON_LLM_PROVIDERS:
            continue  # already has a real LLM report today
        stock = (
            await db.execute(select(Stock).where(Stock.stock_id == rep.stock_id))
        ).scalar_one_or_none()
        name = stock.name if stock else rep.stock_id
        try:
            result = await analysis_engine.analyze(rep.stock_id, db)
            out = await report_generator.generate_report(rep.stock_id, name, result, db)
            if out.provider == "fallback":
                # LLM quota exhausted — keep the screener report; the next
                # scheduled run will try again after quotas reset.
                logger.info("LLM unavailable for %s; keeping screener report", rep.stock_id)
                continue
            await analysis_engine.save_report(
                stock_id=rep.stock_id,
                result=result,
                ai_report=out.markdown,
                ai_provider=out.provider,
                db=db,
                risk_level=out.risk_level,
                target_price=out.target_price,
                stop_loss_price=out.stop_loss_price,
                short_term_outlook=out.short_term_outlook,
                medium_term_outlook=out.medium_term_outlook,
                long_term_outlook=out.long_term_outlook,
            )
            await db.commit()
            logger.info("LLM report generated for %s via %s", rep.stock_id, out.provider)
        except Exception:
            logger.exception("LLM report failed for %s", rep.stock_id)
            await db.rollback()


@router.get("/reports/recent")
async def get_recent_reports(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """報告中心 — the latest report per stock, newest first."""
    reports = (
        await db.execute(
            select(AnalysisReport).order_by(
                AnalysisReport.stock_id, AnalysisReport.report_date.desc()
            )
        )
    ).scalars().all()

    seen: set[str] = set()
    out = []
    for r in reports:
        if r.stock_id in seen:
            continue
        seen.add(r.stock_id)
        stock = (
            await db.execute(select(Stock).where(Stock.stock_id == r.stock_id))
        ).scalar_one_or_none()
        out.append({
            "stock_id": r.stock_id,
            "name": stock.name if stock else r.stock_id,
            "report_date": r.report_date.isoformat() if r.report_date else None,
            "overall_score": float(r.overall_score or 0),
            "overall_signal": r.overall_signal or "neutral",
            "confidence": float(r.confidence or 0),
            "risk_level": r.risk_level,
            "target_price": float(r.target_price) if r.target_price is not None else None,
            "ai_provider": r.ai_provider,
            "has_full_report": r.ai_provider not in _NON_LLM_PROVIDERS,
            "short_term_outlook": r.short_term_outlook,
        })
    out.sort(key=lambda x: (x["report_date"] or "", x["overall_score"]), reverse=True)
    return out[:limit]


@router.get("/{stock_id}/history")
async def get_score_history(
    stock_id: str,
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Score history for one stock — feeds the 報告中心 trend chart."""
    reports = (
        await db.execute(
            select(AnalysisReport)
            .where(AnalysisReport.stock_id == stock_id)
            .order_by(AnalysisReport.report_date.desc())
            .limit(days)
        )
    ).scalars().all()

    return [
        {
            "report_date": r.report_date.isoformat() if r.report_date else None,
            "overall_score": float(r.overall_score or 0),
            "overall_signal": r.overall_signal or "neutral",
            "news": float(r.news_score or 0),
            "fundamental": float(r.fundamental_score or 0),
            "technical": float(r.technical_score or 0),
            "institutional": float(r.institutional_score or 0),
            "macro": float(r.macro_score or 0),
        }
        for r in reversed(reports)  # ascending for charting
    ]


@router.get("/{stock_id}/scores", response_model=AnalysisScoresResponse)
async def get_analysis_scores(
    stock_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get latest dimension scores for a stock (lightweight)."""
    # Get stock name
    stock_result = await db.execute(
        select(Stock).where(Stock.stock_id == stock_id)
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {stock_id} not found")

    # Get latest report
    report_result = await db.execute(
        select(AnalysisReport)
        .where(AnalysisReport.stock_id == stock_id)
        .order_by(AnalysisReport.report_date.desc())
        .limit(1)
    )
    report = report_result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="No analysis report available yet")

    dimensions = [
        DimensionScore(name="消息面", score=float(report.news_score or 0), signal=_dim_signal(float(report.news_score or 0))),
        DimensionScore(name="基本面", score=float(report.fundamental_score or 0), signal=_dim_signal(float(report.fundamental_score or 0))),
        DimensionScore(name="技術面", score=float(report.technical_score or 0), signal=_dim_signal(float(report.technical_score or 0))),
        DimensionScore(name="籌碼面", score=float(report.institutional_score or 0), signal=_dim_signal(float(report.institutional_score or 0))),
        DimensionScore(name="總經面", score=float(report.macro_score or 0), signal=_dim_signal(float(report.macro_score or 0))),
    ]

    return AnalysisScoresResponse(
        stock_id=stock_id,
        stock_name=stock.name,
        report_date=report.report_date,
        overall_score=float(report.overall_score or 0),
        overall_signal=report.overall_signal or "neutral",
        confidence=float(report.confidence or 0),
        dimensions=dimensions,
    )


@router.get("/{stock_id}/report", response_model=AnalysisReportResponse)
async def get_analysis_report(
    stock_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full analysis report with AI-generated content."""
    stock_result = await db.execute(
        select(Stock).where(Stock.stock_id == stock_id)
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {stock_id} not found")

    report_result = await db.execute(
        select(AnalysisReport)
        .where(AnalysisReport.stock_id == stock_id)
        .order_by(AnalysisReport.report_date.desc())
        .limit(1)
    )
    report = report_result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="No analysis report available yet")

    return AnalysisReportResponse(
        stock_id=stock_id,
        stock_name=stock.name,
        report_date=report.report_date,
        overall_score=report.overall_score,
        overall_signal=report.overall_signal,
        confidence=report.confidence,
        news_score=report.news_score,
        fundamental_score=report.fundamental_score,
        technical_score=report.technical_score,
        institutional_score=report.institutional_score,
        macro_score=report.macro_score,
        ai_report_markdown=report.ai_report_markdown,
        ai_provider=report.ai_provider,
        risk_level=report.risk_level,
        short_term_outlook=report.short_term_outlook,
        medium_term_outlook=report.medium_term_outlook,
        long_term_outlook=report.long_term_outlook,
        target_price=report.target_price,
        stop_loss_price=report.stop_loss_price,
        created_at=report.created_at,
    )


@router.post("/{stock_id}/refresh", response_model=AnalysisReportResponse)
async def refresh_analysis(
    stock_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Force re-generate analysis for a stock.

    Runs the full multi-dimension analysis engine and generates a new
    AI report. Saves the result to the database and returns it.
    """
    from app.services.analysis_engine import analysis_engine
    from app.services.report_generator import report_generator

    # Verify stock exists
    stock_result = await db.execute(
        select(Stock).where(Stock.stock_id == stock_id)
    )
    stock = stock_result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {stock_id} not found")

    logger.info("Starting analysis refresh for %s (%s)", stock_id, stock.name)

    try:
        # Step 1: Run multi-dimension analysis
        analysis_result = await analysis_engine.analyze(stock_id, db)

        # Step 2: Generate AI report
        report_output = await report_generator.generate_report(
            stock_id=stock_id,
            stock_name=stock.name,
            analysis=analysis_result,
            db=db,
        )

        # Step 3: Save to database
        await analysis_engine.save_report(
            stock_id=stock_id,
            result=analysis_result,
            ai_report=report_output.markdown,
            ai_provider=report_output.provider,
            db=db,
            risk_level=report_output.risk_level,
            target_price=report_output.target_price,
            stop_loss_price=report_output.stop_loss_price,
            short_term_outlook=report_output.short_term_outlook,
            medium_term_outlook=report_output.medium_term_outlook,
            long_term_outlook=report_output.long_term_outlook,
        )

        logger.info("Analysis refresh complete for %s", stock_id)

        # Step 4: Retrieve the saved report and return it
        report_result = await db.execute(
            select(AnalysisReport)
            .where(AnalysisReport.stock_id == stock_id)
            .order_by(AnalysisReport.report_date.desc())
            .limit(1)
        )
        report = report_result.scalar_one_or_none()

        if not report:
            raise HTTPException(
                status_code=500,
                detail="Report was generated but could not be retrieved",
            )

        return AnalysisReportResponse(
            stock_id=stock_id,
            stock_name=stock.name,
            report_date=report.report_date,
            overall_score=report.overall_score,
            overall_signal=report.overall_signal,
            confidence=report.confidence,
            news_score=report.news_score,
            fundamental_score=report.fundamental_score,
            technical_score=report.technical_score,
            institutional_score=report.institutional_score,
            macro_score=report.macro_score,
            ai_report_markdown=report.ai_report_markdown,
            ai_provider=report.ai_provider,
            risk_level=report.risk_level,
            short_term_outlook=report.short_term_outlook,
            medium_term_outlook=report.medium_term_outlook,
            long_term_outlook=report.long_term_outlook,
            target_price=report.target_price,
            stop_loss_price=report.stop_loss_price,
            created_at=report.created_at,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Analysis refresh failed for %s", stock_id)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis generation failed: {exc}",
        )
