"""Unit tests for the technical indicators calculation service."""

import pytest
from app.services.technical_service import technical_service, TechnicalService


class TestTechnicalService:
    def setup_method(self):
        self.service = TechnicalService()
        # Generate mock price data (60 days of ascending prices)
        self.mock_prices = []
        base_price = 100.0
        for i in range(60):
            price = base_price + i * 0.5 + (i % 3 - 1) * 2  # Uptrend with noise
            self.mock_prices.append({
                "date": f"2024-01-{i+1:02d}" if i < 31 else f"2024-02-{i-30:02d}",
                "open": price - 1,
                "high": price + 2,
                "low": price - 2,
                "close": price,
                "volume": 10000 + i * 100,
            })

    def test_calculate_ma(self):
        closes = [p["close"] for p in self.mock_prices]
        ma = self.service.calculate_ma(closes, [5, 10, 20])
        assert "ma5" in ma
        assert "ma10" in ma
        assert "ma20" in ma
        assert len(ma["ma5"]) == len(closes)

    def test_calculate_rsi(self):
        closes = [p["close"] for p in self.mock_prices]
        rsi = self.service.calculate_rsi(closes, 14)
        assert len(rsi) > 0
        # RSI should be between 0 and 100
        for r in rsi:
            assert 0 <= r <= 100

    def test_calculate_macd(self):
        closes = [p["close"] for p in self.mock_prices]
        macd = self.service.calculate_macd(closes)
        assert "macd" in macd
        assert "signal" in macd
        assert "histogram" in macd

    def test_calculate_kd(self):
        highs = [p["high"] for p in self.mock_prices]
        lows = [p["low"] for p in self.mock_prices]
        closes = [p["close"] for p in self.mock_prices]
        kd = self.service.calculate_kd(highs, lows, closes)
        assert "k" in kd
        assert "d" in kd

    def test_calculate_bollinger(self):
        closes = [p["close"] for p in self.mock_prices]
        bb = self.service.calculate_bollinger(closes)
        assert "upper" in bb
        assert "middle" in bb
        assert "lower" in bb

    def test_calculate_all(self):
        result = self.service.calculate_all(self.mock_prices)
        assert result.indicators is not None
        assert result.signals is not None
        assert -100 <= result.score <= 100
        assert result.summary != ""

    def test_detect_signals(self):
        result = self.service.calculate_all(self.mock_prices)
        # Should detect at least some signals from 60 days of data
        assert isinstance(result.signals, list)

    def test_insufficient_data(self):
        # With very few data points, should handle gracefully
        short_prices = self.mock_prices[:5]
        result = self.service.calculate_all(short_prices)
        assert -100 <= result.score <= 100

    def test_empty_data(self):
        result = self.service.calculate_all([])
        assert result.score == 0
