"""Macro economic analysis API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.macro import (
    MacroDashboardResponse,
    MacroIndicatorItem,
    MacroIndicatorsResponse,
)
from app.services.macro_service import macro_service

router = APIRouter()


@router.get("/dashboard", response_model=MacroDashboardResponse)
async def get_macro_dashboard(
    db: AsyncSession = Depends(get_db),
):
    """Get macro economic overview with all indicators and analysis."""
    indicators = await macro_service.get_macro_indicators(db)
    analysis = macro_service.analyze(indicators)
    score = macro_service.calculate_score(analysis)
    summary = macro_service.generate_summary(score, analysis)

    # Convert MacroIndicator dataclasses to schema objects
    def _to_schema(indicator) -> MacroIndicatorItem | None:
        if indicator is None:
            return None
        return MacroIndicatorItem(
            name=indicator.name,
            value=indicator.value,
            previous_value=indicator.previous_value,
            change=indicator.change,
            trend=indicator.trend,
            updated_at=indicator.updated_at,
        )

    return MacroDashboardResponse(
        interest_rate=_to_schema(analysis.interest_rate),
        taiwan_rate=_to_schema(analysis.taiwan_rate),
        exchange_rate=_to_schema(analysis.exchange_rate),
        taiex=_to_schema(analysis.taiex),
        vix=_to_schema(analysis.vix),
        ten_year_treasury=_to_schema(analysis.ten_year_treasury),
        business_cycle=analysis.business_cycle,
        rate_cycle=analysis.rate_cycle,
        score=score,
        summary=summary,
    )


@router.get("/indicators", response_model=MacroIndicatorsResponse)
async def get_macro_indicators(
    db: AsyncSession = Depends(get_db),
):
    """Get raw macro indicator data."""
    indicators_data = await macro_service.get_macro_indicators(db)

    items = []
    for key, value in indicators_data.items():
        if isinstance(value, dict) and "value" in value:
            items.append(
                MacroIndicatorItem(
                    name=key,
                    value=value.get("value"),
                    previous_value=value.get("previous_value"),
                    change=value.get("change"),
                    trend=value.get("trend"),
                    updated_at=value.get("updated_at"),
                )
            )

    return MacroIndicatorsResponse(indicators=items)
