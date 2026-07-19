"""Unit tests for the backtest signal/indicator helpers."""

from app.routers.backtest import _rsi, _signals_ma_cross, _signals_rsi, _sma


def test_sma_basic():
    out = _sma([1, 2, 3, 4, 5], 3)
    assert out[:2] == [None, None]
    assert out[2] == 2.0
    assert out[4] == 4.0


def test_ma_cross_golden_and_death():
    # Down then sharply up → golden cross; then sharply down → death cross.
    closes = [10.0] * 10 + [8.0] * 5 + [12.0] * 10 + [7.0] * 10
    sig = _signals_ma_cross(closes, fast=3, slow=6)
    assert "buy" in sig
    assert "sell" in sig
    assert sig.index("buy") < len(closes) - 10 + 6  # buy happens on the way up


def test_rsi_range():
    closes = [100 + (i % 7) - 3 for i in range(60)]
    rsi = _rsi(closes)
    vals = [v for v in rsi if v is not None]
    assert vals and all(0 <= v <= 100 for v in vals)


def test_rsi_signals_on_swings():
    # Long slide (oversold) then strong rally → RSI crosses back up over 30.
    closes = [100 - i * 1.5 for i in range(25)] + [62 + i * 2.0 for i in range(25)]
    sig = _signals_rsi(closes)
    assert "buy" in sig
