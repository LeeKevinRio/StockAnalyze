"""Institutional and margin trading API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.institutional import (
    InstitutionalAnalysis,
    InstitutionalDataResponse,
    InstitutionalDayData,
    InstitutionalSummaryResponse,
    MarginAnalysis,
    MarginDataResponse,
    MarginDayData,
)
from app.services.institutional_service import institutional_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{stock_id}",
    response_model=InstitutionalDataResponse,
    summary="取得三大法人買賣超資料與分析",
    description="回傳三大法人（外資、投信、自營商）每日買賣超資料及趨勢分析",
)
async def get_institutional_data(
    stock_id: str,
    days: int = Query(30, ge=5, le=120, description="查詢天數"),
    db: AsyncSession = Depends(get_db),
):
    """Get institutional trading data with analysis."""
    # On-demand: backfill institutional + margin data if this stock has none yet.
    from app.services.ondemand import ensure_institutional
    await ensure_institutional(stock_id, db)

    data = await institutional_service.get_institutional_data(stock_id, db, days)

    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"找不到股票 {stock_id} 的法人買賣超資料",
        )

    analysis_result = institutional_service.analyze_institutional(data)

    # We also need margin data for the full score
    margin_data = await institutional_service.get_margin_data(stock_id, db, days)
    margin_result = institutional_service.analyze_margin(margin_data)
    score = institutional_service.calculate_score(analysis_result, margin_result)
    summary = institutional_service.generate_summary(score, analysis_result, margin_result)

    return InstitutionalDataResponse(
        stock_id=stock_id,
        data=[
            InstitutionalDayData(
                date=d["date"],
                foreign_net=d["foreign_net"],
                trust_net=d["trust_net"],
                dealer_net=d["dealer_net"],
                total_net=d["total_net"],
            )
            for d in data
        ],
        analysis=InstitutionalAnalysis(
            foreign_trend=analysis_result.foreign_trend,
            trust_trend=analysis_result.trust_trend,
            dealer_trend=analysis_result.dealer_trend,
            foreign_consecutive_days=analysis_result.foreign_consecutive_days,
            cumulative_foreign_20d=analysis_result.cumulative_foreign_20d,
            cumulative_trust_20d=analysis_result.cumulative_trust_20d,
            score=score,
            summary=summary,
        ),
    )


@router.get(
    "/{stock_id}/margin",
    response_model=MarginDataResponse,
    summary="取得融資融券資料與分析",
    description="回傳融資融券餘額、使用率及趨勢分析",
)
async def get_margin_data(
    stock_id: str,
    days: int = Query(30, ge=5, le=120, description="查詢天數"),
    db: AsyncSession = Depends(get_db),
):
    """Get margin trading data with analysis."""
    data = await institutional_service.get_margin_data(stock_id, db, days)

    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"找不到股票 {stock_id} 的融資融券資料",
        )

    margin_result = institutional_service.analyze_margin(data)

    # Build per-day change values
    margin_day_data: list[MarginDayData] = []
    for i, d in enumerate(data):
        margin_change = 0
        short_change = 0
        if i > 0:
            margin_change = d["margin_balance"] - data[i - 1]["margin_balance"]
            short_change = d["short_balance"] - data[i - 1]["short_balance"]

        margin_day_data.append(
            MarginDayData(
                date=d["date"],
                margin_balance=d["margin_balance"],
                margin_change=margin_change,
                short_balance=d["short_balance"],
                short_change=short_change,
                utilization=d["margin_utilization"],
            )
        )

    # Generate summary for margin specifically
    summary_parts = []
    if margin_result.margin_trend == "increasing":
        summary_parts.append("融資餘額呈增加趨勢，散戶看多氣氛升溫。")
    elif margin_result.margin_trend == "decreasing":
        summary_parts.append("融資餘額呈下降趨勢，籌碼面逐步沉澱。")
    else:
        summary_parts.append("融資餘額維持穩定。")

    if margin_result.short_trend == "increasing":
        summary_parts.append("融券餘額增加，空方力道上升。")
    elif margin_result.short_trend == "decreasing":
        summary_parts.append("融券餘額減少，空方回補中。")

    if margin_result.squeeze_potential:
        summary_parts.append("融券水位偏高，存在軋空潛力。")

    util_desc = {"high": "偏高", "medium": "中等", "low": "偏低"}
    summary_parts.append(f"融資使用率 {margin_result.latest_utilization:.1f}%（{util_desc.get(margin_result.utilization_level, '')}）。")

    return MarginDataResponse(
        stock_id=stock_id,
        data=margin_day_data,
        analysis=MarginAnalysis(
            margin_trend=margin_result.margin_trend,
            short_trend=margin_result.short_trend,
            utilization_level=margin_result.utilization_level,
            squeeze_potential=margin_result.squeeze_potential,
            summary="".join(summary_parts),
        ),
    )


@router.get(
    "/{stock_id}/summary",
    response_model=InstitutionalSummaryResponse,
    summary="取得籌碼面快速摘要",
    description="回傳籌碼面評分與簡要摘要，適合快速查看",
)
async def get_institutional_summary(
    stock_id: str,
    days: int = Query(30, ge=5, le=120, description="查詢天數"),
    db: AsyncSession = Depends(get_db),
):
    """Get quick summary with score combining institutional + margin data."""
    inst_data = await institutional_service.get_institutional_data(stock_id, db, days)
    margin_data = await institutional_service.get_margin_data(stock_id, db, days)

    if not inst_data and not margin_data:
        raise HTTPException(
            status_code=404,
            detail=f"找不到股票 {stock_id} 的籌碼相關資料",
        )

    inst_result = institutional_service.analyze_institutional(inst_data)
    margin_result = institutional_service.analyze_margin(margin_data)

    score = institutional_service.calculate_score(inst_result, margin_result)
    summary = institutional_service.generate_summary(score, inst_result, margin_result)

    # Determine overall signal
    if score >= 20:
        signal = "bullish"
    elif score <= -20:
        signal = "bearish"
    else:
        signal = "neutral"

    return InstitutionalSummaryResponse(
        stock_id=stock_id,
        score=round(score, 1),
        signal=signal,
        summary=summary,
        foreign_trend=inst_result.foreign_trend,
        trust_trend=inst_result.trust_trend,
    )
