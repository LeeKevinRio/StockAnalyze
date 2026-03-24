"""Analysis-related API endpoints."""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.analysis import AnalysisReport
from app.models.stock import Stock
from app.schemas.analysis import AnalysisReportResponse, AnalysisScoresResponse, DimensionScore

logger = logging.getLogger(__name__)

router = APIRouter()


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
