"""Simple strategy backtesting over stored daily prices.

Simulates rule-based strategies (MA cross, RSI mean-reversion) against
buy-and-hold on the same window. Educational tool — close-price fills,
no fees/slippage/position sizing.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stock import Stock, StockPrice

logger = logging.getLogger(__name__)

router = APIRouter()


def _sma(values: list[float], window: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    total = 0.0
    for i, v in enumerate(values):
        total += v
        if i >= window:
            total -= values[i - window]
        if i >= window - 1:
            out[i] = total / window
    return out


def _rsi(values: list[float], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return out
    gains = losses = 0.0
    for i in range(1, period + 1):
        diff = values[i] - values[i - 1]
        gains += max(diff, 0)
        losses += max(-diff, 0)
    avg_gain, avg_loss = gains / period, losses / period
    out[period] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    for i in range(period + 1, len(values)):
        diff = values[i] - values[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(diff, 0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-diff, 0)) / period
        out[i] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    return out


def _signals_ma_cross(closes: list[float], fast: int, slow: int) -> list[str | None]:
    """'buy' on golden cross, 'sell' on death cross."""
    fast_ma, slow_ma = _sma(closes, fast), _sma(closes, slow)
    sig: list[str | None] = [None] * len(closes)
    for i in range(1, len(closes)):
        if None in (fast_ma[i], slow_ma[i], fast_ma[i - 1], slow_ma[i - 1]):
            continue
        if fast_ma[i - 1] <= slow_ma[i - 1] and fast_ma[i] > slow_ma[i]:
            sig[i] = "buy"
        elif fast_ma[i - 1] >= slow_ma[i - 1] and fast_ma[i] < slow_ma[i]:
            sig[i] = "sell"
    return sig


def _signals_rsi(closes: list[float], low: int = 30, high: int = 70) -> list[str | None]:
    """'buy' when RSI crosses up out of oversold, 'sell' when crossing down from overbought."""
    rsi = _rsi(closes)
    sig: list[str | None] = [None] * len(closes)
    for i in range(1, len(closes)):
        if rsi[i] is None or rsi[i - 1] is None:
            continue
        if rsi[i - 1] < low <= rsi[i]:
            sig[i] = "buy"
        elif rsi[i - 1] > high >= rsi[i]:
            sig[i] = "sell"
    return sig


@router.get("/{stock_id}")
async def run_backtest(
    stock_id: str,
    strategy: str = Query("ma_cross", pattern="^(ma_cross|rsi)$"),
    days: int = Query(250, ge=60, le=365),
    fast: int = Query(5, ge=2, le=60),
    slow: int = Query(20, ge=5, le=120),
    db: AsyncSession = Depends(get_db),
):
    """Run a rule-based backtest vs buy-and-hold on stored daily closes."""
    if fast >= slow:
        raise HTTPException(status_code=422, detail="fast must be < slow")

    stock = (
        await db.execute(select(Stock).where(Stock.stock_id == stock_id))
    ).scalar_one_or_none()
    if stock is None:
        raise HTTPException(status_code=404, detail=f"Stock {stock_id} not found")

    from app.services.stock_service import ensure_price_history

    await ensure_price_history(stock_id, db)

    rows = (
        await db.execute(
            select(StockPrice)
            .where(StockPrice.stock_id == stock_id)
            .order_by(StockPrice.date.desc())
            .limit(days)
        )
    ).scalars().all()
    rows = list(reversed(rows))
    dates = [r.date.isoformat() for r in rows if r.close is not None]
    closes = [float(r.close) for r in rows if r.close is not None]
    if len(closes) < 30:
        raise HTTPException(status_code=422, detail="價格資料不足(需至少 30 個交易日)")

    signals = (
        _signals_ma_cross(closes, fast, slow)
        if strategy == "ma_cross"
        else _signals_rsi(closes)
    )

    # Simulate: all-in on buy, all-out on sell, close-price fills.
    cash, shares = 1.0, 0.0
    trades: list[dict] = []
    curve: list[dict] = []
    entry_price: float | None = None
    wins = losses = 0
    peak, max_drawdown = 0.0, 0.0

    for i, (d, c) in enumerate(zip(dates, closes)):
        if signals[i] == "buy" and shares == 0:
            shares = cash / c
            cash = 0.0
            entry_price = c
            trades.append({"date": d, "action": "buy", "price": round(c, 2)})
        elif signals[i] == "sell" and shares > 0:
            cash = shares * c
            shares = 0.0
            if entry_price is not None:
                if c > entry_price:
                    wins += 1
                else:
                    losses += 1
            trades.append({"date": d, "action": "sell", "price": round(c, 2)})

        equity = cash + shares * c
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
        curve.append({
            "date": d,
            "strategy": round(equity * 100, 2),           # indexed to 100
            "buy_hold": round(c / closes[0] * 100, 2),
        })

    final = cash + shares * closes[-1]
    closed = wins + losses

    return {
        "stock_id": stock_id,
        "name": stock.name,
        "strategy": strategy,
        "params": {"fast": fast, "slow": slow} if strategy == "ma_cross" else {"low": 30, "high": 70},
        "days": len(closes),
        "start_date": dates[0],
        "end_date": dates[-1],
        "strategy_return_pct": round((final - 1) * 100, 2),
        "buy_hold_return_pct": round((closes[-1] / closes[0] - 1) * 100, 2),
        "trade_count": len(trades),
        "win_rate": round(wins / closed * 100, 1) if closed else None,
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "in_position": shares > 0,
        "trades": trades[-20:],
        "curve": curve,
    }
