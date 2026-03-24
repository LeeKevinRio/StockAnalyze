"""Technical indicators calculation engine.

Pure computation service -- no database or I/O dependencies.
All calculations use plain Python / math (no numpy / pandas required).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------

@dataclass
class TechnicalResult:
    """Aggregated result of all technical indicator calculations."""

    indicators: dict = field(default_factory=dict)  # Raw indicator values
    signals: list[dict] = field(default_factory=list)  # Detected signals
    score: float = 0.0  # -100 to +100
    summary: str = ""  # Brief Chinese text summary


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class TechnicalService:
    """Calculate technical indicators from OHLCV price data."""

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def calculate_all(self, prices: list[dict]) -> TechnicalResult:
        """Calculate all indicators from OHLCV price data.

        Args:
            prices: list of ``{date, open, high, low, close, volume}``
                sorted by date **ascending**.

        Returns:
            A :class:`TechnicalResult` with indicators, signals, score
            and a Chinese summary.
        """
        if not prices:
            return TechnicalResult(
                summary="無足夠價格資料進行技術分析。",
            )

        closes = [float(p["close"]) for p in prices if p.get("close") is not None]
        highs = [float(p["high"]) for p in prices if p.get("high") is not None]
        lows = [float(p["low"]) for p in prices if p.get("low") is not None]
        volumes = [int(p["volume"]) for p in prices if p.get("volume") is not None]

        if len(closes) < 5:
            return TechnicalResult(
                summary="價格資料不足（少於5筆），無法計算技術指標。",
            )

        indicators: dict = {}

        # Moving Averages
        indicators["ma"] = self.calculate_ma(closes)

        # MACD
        if len(closes) >= 26:
            indicators["macd"] = self.calculate_macd(closes)

        # RSI
        if len(closes) >= 15:
            indicators["rsi"] = self.calculate_rsi(closes)

        # KD (Stochastic)
        if len(highs) >= 9 and len(lows) >= 9 and len(closes) >= 9:
            indicators["kd"] = self.calculate_kd(highs, lows, closes)

        # Bollinger Bands
        if len(closes) >= 20:
            indicators["bollinger"] = self.calculate_bollinger(closes)

        # Volume analysis
        if volumes and closes and len(volumes) == len(closes):
            indicators["volume_analysis"] = self.calculate_volume_analysis(volumes, closes)

        # Detect signals
        signals = self.detect_signals(indicators)

        # Calculate score
        score = self.calculate_score(indicators, signals)

        # Generate summary
        summary = self._generate_summary(score, indicators, signals)

        return TechnicalResult(
            indicators=indicators,
            signals=signals,
            score=round(score, 1),
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Moving Averages
    # ------------------------------------------------------------------

    def calculate_ma(
        self,
        closes: list[float],
        periods: list[int] | None = None,
    ) -> dict:
        """Simple moving averages.

        Returns:
            ``{ma5: [...], ma10: [...], ma20: [...], ma60: [...]}``
            Each list is the same length as *closes*; leading values that
            cannot be computed are ``None``.
        """
        if periods is None:
            periods = [5, 10, 20, 60]

        result: dict[str, list[float | None]] = {}
        for period in periods:
            key = f"ma{period}"
            ma_values: list[float | None] = []
            for i in range(len(closes)):
                if i < period - 1:
                    ma_values.append(None)
                else:
                    window = closes[i - period + 1: i + 1]
                    ma_values.append(round(sum(window) / period, 2))
            result[key] = ma_values
        return result

    # ------------------------------------------------------------------
    # Exponential Moving Average
    # ------------------------------------------------------------------

    def calculate_ema(self, closes: list[float], period: int) -> list[float]:
        """Exponential moving average.

        Uses SMA of the first *period* values as the seed, then applies
        the standard EMA multiplier ``2 / (period + 1)``.
        """
        if len(closes) < period:
            return []

        multiplier = 2.0 / (period + 1)
        ema_values: list[float] = []

        # Seed: SMA of first `period` elements
        seed = sum(closes[:period]) / period
        ema_values.append(round(seed, 4))

        for i in range(period, len(closes)):
            prev = ema_values[-1]
            val = (closes[i] - prev) * multiplier + prev
            ema_values.append(round(val, 4))

        return ema_values

    # ------------------------------------------------------------------
    # MACD
    # ------------------------------------------------------------------

    def calculate_macd(
        self,
        closes: list[float],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> dict:
        """MACD (Moving Average Convergence Divergence).

        Returns:
            ``{macd: [...], signal: [...], histogram: [...]}``
        """
        if len(closes) < slow:
            return {"macd": [], "signal": [], "histogram": []}

        ema_fast = self.calculate_ema(closes, fast)
        ema_slow = self.calculate_ema(closes, slow)

        # Align: ema_fast starts at index ``fast``, ema_slow at ``slow``
        # We trim ema_fast so both lists end at the same index.
        offset = slow - fast
        ema_fast_aligned = ema_fast[offset:]

        length = min(len(ema_fast_aligned), len(ema_slow))
        macd_line = [
            round(ema_fast_aligned[i] - ema_slow[i], 4)
            for i in range(length)
        ]

        # Signal line: EMA of MACD line
        if len(macd_line) >= signal:
            signal_line = self._ema_from_values(macd_line, signal)
        else:
            signal_line = []

        # Histogram
        sig_offset = len(macd_line) - len(signal_line)
        histogram = [
            round(macd_line[sig_offset + i] - signal_line[i], 4)
            for i in range(len(signal_line))
        ]

        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram,
        }

    # ------------------------------------------------------------------
    # RSI
    # ------------------------------------------------------------------

    def calculate_rsi(self, closes: list[float], period: int = 14) -> list[float]:
        """RSI (Relative Strength Index).

        Uses the Wilder smoothing method (exponential moving average of
        gains and losses).
        """
        if len(closes) < period + 1:
            return []

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

        gains = [max(d, 0) for d in deltas]
        losses = [abs(min(d, 0)) for d in deltas]

        # Seed averages from first `period` deltas
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        rsi_values: list[float] = []

        # First RSI value
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(round(100.0 - 100.0 / (1.0 + rs), 2))

        # Subsequent values using Wilder smoothing
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0:
                rsi_values.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi_values.append(round(100.0 - 100.0 / (1.0 + rs), 2))

        return rsi_values

    # ------------------------------------------------------------------
    # KD (Stochastic Oscillator)
    # ------------------------------------------------------------------

    def calculate_kd(
        self,
        highs: list[float],
        lows: list[float],
        closes: list[float],
        k_period: int = 9,
        k_smooth: int = 3,
        d_smooth: int = 3,
    ) -> dict:
        """KD / Stochastic Oscillator.

        Returns:
            ``{k: [...], d: [...]}``
        """
        n = min(len(highs), len(lows), len(closes))
        if n < k_period:
            return {"k": [], "d": []}

        # Raw %K (RSV)
        rsv_values: list[float] = []
        for i in range(k_period - 1, n):
            window_high = max(highs[i - k_period + 1: i + 1])
            window_low = min(lows[i - k_period + 1: i + 1])
            if window_high == window_low:
                rsv_values.append(50.0)
            else:
                rsv = (closes[i] - window_low) / (window_high - window_low) * 100.0
                rsv_values.append(round(rsv, 2))

        # Smooth %K using SMA
        k_values: list[float] = self._sma(rsv_values, k_smooth)

        # %D = SMA of %K
        d_values: list[float] = self._sma(k_values, d_smooth)

        return {"k": k_values, "d": d_values}

    # ------------------------------------------------------------------
    # Bollinger Bands
    # ------------------------------------------------------------------

    def calculate_bollinger(
        self,
        closes: list[float],
        period: int = 20,
        std_dev: float = 2.0,
    ) -> dict:
        """Bollinger Bands.

        Returns:
            ``{upper: [...], middle: [...], lower: [...]}``
        """
        if len(closes) < period:
            return {"upper": [], "middle": [], "lower": []}

        upper: list[float] = []
        middle: list[float] = []
        lower: list[float] = []

        for i in range(period - 1, len(closes)):
            window = closes[i - period + 1: i + 1]
            mean = sum(window) / period
            variance = sum((x - mean) ** 2 for x in window) / period
            std = math.sqrt(variance)

            middle.append(round(mean, 2))
            upper.append(round(mean + std_dev * std, 2))
            lower.append(round(mean - std_dev * std, 2))

        return {"upper": upper, "middle": middle, "lower": lower}

    # ------------------------------------------------------------------
    # Volume Analysis
    # ------------------------------------------------------------------

    def calculate_volume_analysis(
        self,
        volumes: list[int],
        closes: list[float],
    ) -> dict:
        """Analyse volume patterns.

        Returns dict with:
        - avg_volume_5d / 20d
        - latest_volume
        - volume_ratio (latest vs 20d avg)
        - volume_trend ("increasing" / "decreasing" / "stable")
        - price_volume_divergence (bool)
        """
        if not volumes or not closes:
            return {}

        n = len(volumes)
        latest_volume = volumes[-1]

        avg_5d = sum(volumes[-5:]) / min(5, n) if n >= 1 else 0
        avg_20d = sum(volumes[-20:]) / min(20, n) if n >= 1 else 0
        volume_ratio = round(latest_volume / avg_20d, 2) if avg_20d > 0 else 0.0

        # Volume trend: compare recent 5d avg vs prior 5d avg
        if n >= 10:
            recent_avg = sum(volumes[-5:]) / 5
            prior_avg = sum(volumes[-10:-5]) / 5
            if prior_avg > 0:
                change_pct = (recent_avg - prior_avg) / prior_avg
                if change_pct > 0.2:
                    volume_trend = "increasing"
                elif change_pct < -0.2:
                    volume_trend = "decreasing"
                else:
                    volume_trend = "stable"
            else:
                volume_trend = "stable"
        else:
            volume_trend = "stable"

        # Price-volume divergence: price rising but volume declining (or vice versa)
        divergence = False
        if n >= 10:
            price_change = closes[-1] - closes[-5] if len(closes) >= 5 else 0
            vol_recent = sum(volumes[-5:]) / 5
            vol_prior = sum(volumes[-10:-5]) / 5
            if price_change > 0 and vol_prior > 0 and (vol_recent / vol_prior) < 0.8:
                divergence = True  # price up, volume down
            elif price_change < 0 and vol_prior > 0 and (vol_recent / vol_prior) > 1.2:
                divergence = True  # price down, volume up

        return {
            "avg_volume_5d": round(avg_5d),
            "avg_volume_20d": round(avg_20d),
            "latest_volume": latest_volume,
            "volume_ratio": volume_ratio,
            "volume_trend": volume_trend,
            "price_volume_divergence": divergence,
        }

    # ------------------------------------------------------------------
    # Signal Detection
    # ------------------------------------------------------------------

    def detect_signals(self, indicators: dict) -> list[dict]:
        """Detect buy/sell signals from calculated indicators.

        Returns:
            list of ``{signal_type, direction, description, strength}``
        """
        signals: list[dict] = []

        # --- MA crossover ---
        self._detect_ma_signals(indicators, signals)

        # --- MACD crossover ---
        self._detect_macd_signals(indicators, signals)

        # --- RSI signals ---
        self._detect_rsi_signals(indicators, signals)

        # --- KD signals ---
        self._detect_kd_signals(indicators, signals)

        # --- Bollinger Band signals ---
        self._detect_bollinger_signals(indicators, signals)

        # --- Volume surge ---
        self._detect_volume_signals(indicators, signals)

        return signals

    # ------------------------------------------------------------------
    # Score Calculation
    # ------------------------------------------------------------------

    def calculate_score(self, indicators: dict, signals: list[dict]) -> float:
        """Calculate technical dimension score (-100 to +100).

        Scoring breakdown:
        - MA alignment: +/-20
        - Price vs MA20: +/-10
        - MACD signal: +/-15, zero line +/-5
        - RSI zone: +/-10
        - KD zone: +/-10
        - Bollinger position: +/-5
        - Volume confirmation: +/-10
        - Net signal count * 5
        """
        score = 0.0

        # --- MA alignment ---
        ma_data = indicators.get("ma", {})
        score += self._score_ma_alignment(ma_data)

        # --- Price vs MA20 ---
        ma20 = ma_data.get("ma20", [])
        if ma20:
            last_ma20 = self._last_valid(ma20)
            ma5 = ma_data.get("ma5", [])
            last_price_proxy = self._last_valid(ma5)  # ma5 approximates price
            if last_ma20 is not None and last_price_proxy is not None:
                if last_price_proxy > last_ma20:
                    score += 10
                else:
                    score -= 10

        # --- MACD ---
        macd_data = indicators.get("macd", {})
        if macd_data:
            score += self._score_macd(macd_data)

        # --- RSI ---
        rsi_data = indicators.get("rsi", [])
        if rsi_data:
            score += self._score_rsi(rsi_data)

        # --- KD ---
        kd_data = indicators.get("kd", {})
        if kd_data:
            score += self._score_kd(kd_data)

        # --- Bollinger ---
        bb_data = indicators.get("bollinger", {})
        if bb_data:
            score += self._score_bollinger(bb_data)

        # --- Volume confirmation ---
        vol_data = indicators.get("volume_analysis", {})
        if vol_data:
            score += self._score_volume(vol_data, indicators)

        # --- Signal count ---
        bullish_count = sum(1 for s in signals if s["direction"] == "bullish")
        bearish_count = sum(1 for s in signals if s["direction"] == "bearish")
        score += (bullish_count - bearish_count) * 5

        # Clamp to [-100, 100]
        return max(-100.0, min(100.0, score))

    # ==================================================================
    # Private helpers
    # ==================================================================

    def _ema_from_values(self, values: list[float], period: int) -> list[float]:
        """Compute EMA on an arbitrary list of floats."""
        if len(values) < period:
            return []
        multiplier = 2.0 / (period + 1)
        seed = sum(values[:period]) / period
        ema = [round(seed, 4)]
        for i in range(period, len(values)):
            val = (values[i] - ema[-1]) * multiplier + ema[-1]
            ema.append(round(val, 4))
        return ema

    def _sma(self, values: list[float], period: int) -> list[float]:
        """Simple moving average for a list of floats."""
        result: list[float] = []
        for i in range(len(values)):
            if i < period - 1:
                # Not enough data yet -- use available values (progressive smoothing)
                result.append(round(sum(values[: i + 1]) / (i + 1), 2))
            else:
                window = values[i - period + 1: i + 1]
                result.append(round(sum(window) / period, 2))
        return result

    @staticmethod
    def _last_valid(series: list) -> float | None:
        """Return the last non-None value in a list."""
        for v in reversed(series):
            if v is not None:
                return float(v)
        return None

    # --- Signal detection helpers ---

    def _detect_ma_signals(self, indicators: dict, signals: list[dict]) -> None:
        ma = indicators.get("ma", {})
        ma5 = ma.get("ma5", [])
        ma20 = ma.get("ma20", [])

        if len(ma5) >= 2 and len(ma20) >= 2:
            prev_5 = self._last_valid(ma5[:-1])
            curr_5 = self._last_valid(ma5)
            prev_20 = self._last_valid(ma20[:-1])
            curr_20 = self._last_valid(ma20)

            if all(v is not None for v in (prev_5, curr_5, prev_20, curr_20)):
                # Golden cross: MA5 crosses above MA20
                if prev_5 <= prev_20 and curr_5 > curr_20:
                    signals.append({
                        "signal_type": "ma_crossover",
                        "direction": "bullish",
                        "description": "MA5 向上突破 MA20（黃金交叉）",
                        "strength": "strong",
                    })
                # Death cross: MA5 crosses below MA20
                elif prev_5 >= prev_20 and curr_5 < curr_20:
                    signals.append({
                        "signal_type": "ma_crossover",
                        "direction": "bearish",
                        "description": "MA5 向下跌破 MA20（死亡交叉）",
                        "strength": "strong",
                    })

    def _detect_macd_signals(self, indicators: dict, signals: list[dict]) -> None:
        macd_data = indicators.get("macd", {})
        macd_line = macd_data.get("macd", [])
        signal_line = macd_data.get("signal", [])
        histogram = macd_data.get("histogram", [])

        if len(histogram) >= 2:
            prev_h = histogram[-2]
            curr_h = histogram[-1]
            # MACD crosses above signal (histogram turns positive)
            if prev_h <= 0 and curr_h > 0:
                signals.append({
                    "signal_type": "macd_crossover",
                    "direction": "bullish",
                    "description": "MACD 向上突破訊號線（多頭交叉）",
                    "strength": "medium",
                })
            # MACD crosses below signal
            elif prev_h >= 0 and curr_h < 0:
                signals.append({
                    "signal_type": "macd_crossover",
                    "direction": "bearish",
                    "description": "MACD 向下跌破訊號線（空頭交叉）",
                    "strength": "medium",
                })

    def _detect_rsi_signals(self, indicators: dict, signals: list[dict]) -> None:
        rsi_values = indicators.get("rsi", [])
        if not rsi_values:
            return
        latest_rsi = rsi_values[-1]

        if latest_rsi > 70:
            signals.append({
                "signal_type": "rsi_overbought",
                "direction": "bearish",
                "description": f"RSI 超買（{latest_rsi:.1f}），短線有回檔風險",
                "strength": "medium" if latest_rsi <= 80 else "strong",
            })
        elif latest_rsi < 30:
            signals.append({
                "signal_type": "rsi_oversold",
                "direction": "bullish",
                "description": f"RSI 超賣（{latest_rsi:.1f}），短線有反彈機會",
                "strength": "medium" if latest_rsi >= 20 else "strong",
            })

    def _detect_kd_signals(self, indicators: dict, signals: list[dict]) -> None:
        kd = indicators.get("kd", {})
        k_values = kd.get("k", [])
        d_values = kd.get("d", [])

        if not k_values or not d_values:
            return

        latest_k = k_values[-1]
        latest_d = d_values[-1]

        # Overbought / Oversold
        if latest_k > 80 and latest_d > 80:
            signals.append({
                "signal_type": "kd_overbought",
                "direction": "bearish",
                "description": f"KD 超買區（K:{latest_k:.1f}, D:{latest_d:.1f}）",
                "strength": "medium",
            })
        elif latest_k < 20 and latest_d < 20:
            signals.append({
                "signal_type": "kd_oversold",
                "direction": "bullish",
                "description": f"KD 超賣區（K:{latest_k:.1f}, D:{latest_d:.1f}）",
                "strength": "medium",
            })

        # KD crossover
        if len(k_values) >= 2 and len(d_values) >= 2:
            prev_k = k_values[-2]
            prev_d = d_values[-2]
            if prev_k <= prev_d and latest_k > latest_d:
                strength = "strong" if latest_k < 30 else "medium"
                signals.append({
                    "signal_type": "kd_crossover",
                    "direction": "bullish",
                    "description": "K 線向上突破 D 線（KD 黃金交叉）",
                    "strength": strength,
                })
            elif prev_k >= prev_d and latest_k < latest_d:
                strength = "strong" if latest_k > 70 else "medium"
                signals.append({
                    "signal_type": "kd_crossover",
                    "direction": "bearish",
                    "description": "K 線向下跌破 D 線（KD 死亡交叉）",
                    "strength": strength,
                })

    def _detect_bollinger_signals(self, indicators: dict, signals: list[dict]) -> None:
        bb = indicators.get("bollinger", {})
        upper = bb.get("upper", [])
        lower = bb.get("lower", [])
        middle = bb.get("middle", [])

        ma5 = indicators.get("ma", {}).get("ma5", [])
        if not upper or not lower or not ma5:
            return

        price_proxy = self._last_valid(ma5)
        u = upper[-1]
        l = lower[-1]

        if price_proxy is not None:
            if price_proxy > u:
                signals.append({
                    "signal_type": "bollinger_breakout",
                    "direction": "bearish",
                    "description": "股價突破布林通道上軌，短線可能過熱",
                    "strength": "medium",
                })
            elif price_proxy < l:
                signals.append({
                    "signal_type": "bollinger_breakout",
                    "direction": "bullish",
                    "description": "股價跌破布林通道下軌，短線可能超跌",
                    "strength": "medium",
                })

    def _detect_volume_signals(self, indicators: dict, signals: list[dict]) -> None:
        vol = indicators.get("volume_analysis", {})
        ratio = vol.get("volume_ratio", 0)
        if ratio >= 2.0:
            signals.append({
                "signal_type": "volume_surge",
                "direction": "bullish",  # direction depends on price; default bullish
                "description": f"成交量爆量（為20日均量的 {ratio:.1f} 倍），關注變盤訊號",
                "strength": "strong" if ratio >= 3.0 else "medium",
            })

        if vol.get("price_volume_divergence"):
            signals.append({
                "signal_type": "volume_divergence",
                "direction": "bearish",
                "description": "價量背離，注意趨勢反轉風險",
                "strength": "weak",
            })

    # --- Score component helpers ---

    def _score_ma_alignment(self, ma_data: dict) -> float:
        """Score based on MA alignment (bull/bear order)."""
        ma5 = self._last_valid(ma_data.get("ma5", []))
        ma10 = self._last_valid(ma_data.get("ma10", []))
        ma20 = self._last_valid(ma_data.get("ma20", []))
        ma60 = self._last_valid(ma_data.get("ma60", []))

        vals = [v for v in [ma5, ma10, ma20, ma60] if v is not None]
        if len(vals) < 3:
            return 0.0

        # Check if in perfect bullish order (short > long)
        is_bullish = all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1))
        is_bearish = all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1))

        if is_bullish:
            return 20.0
        elif is_bearish:
            return -20.0

        # Partial alignment: check MA5 vs MA20
        if ma5 is not None and ma20 is not None:
            return 10.0 if ma5 > ma20 else -10.0
        return 0.0

    def _score_macd(self, macd_data: dict) -> float:
        """Score based on MACD state."""
        score = 0.0
        histogram = macd_data.get("histogram", [])
        macd_line = macd_data.get("macd", [])

        if histogram and len(histogram) >= 2:
            prev_h = histogram[-2]
            curr_h = histogram[-1]
            # Crossover
            if prev_h <= 0 < curr_h:
                score += 15
            elif prev_h >= 0 > curr_h:
                score -= 15

        if macd_line:
            latest = macd_line[-1]
            if latest > 0:
                score += 5
            elif latest < 0:
                score -= 5

        return score

    def _score_rsi(self, rsi_data: list[float]) -> float:
        """Score based on RSI zone."""
        if not rsi_data:
            return 0.0
        latest = rsi_data[-1]
        if latest > 70:
            return -10.0
        elif latest > 50:
            return 5.0
        elif latest > 30:
            return -5.0
        else:
            return 10.0  # oversold bounce potential

    def _score_kd(self, kd_data: dict) -> float:
        """Score based on KD zone and crossover."""
        k_values = kd_data.get("k", [])
        d_values = kd_data.get("d", [])
        if not k_values or not d_values:
            return 0.0

        score = 0.0
        k = k_values[-1]
        d = d_values[-1]

        if k > 80:
            score -= 10.0
        elif k < 20:
            score += 10.0
        elif k > 50:
            score += 5.0
        else:
            score -= 5.0

        return score

    def _score_bollinger(self, bb_data: dict) -> float:
        """Score based on Bollinger Band position."""
        upper = bb_data.get("upper", [])
        lower = bb_data.get("lower", [])
        middle = bb_data.get("middle", [])

        if not upper or not lower or not middle:
            return 0.0

        u = upper[-1]
        l = lower[-1]
        m = middle[-1]

        band_width = u - l
        if band_width == 0:
            return 0.0

        # Estimate price position within band using middle as reference
        # Closer to upper = resistance (-5), closer to lower = support (+5)
        # We use middle itself as a neutral anchor
        mid_ratio = 0.5  # neutral if we only have BB data
        # If we're just using middle, return 0 -- real price is checked
        # in calculate_score with MA5 proxy
        return 0.0

    def _score_volume(self, vol_data: dict, indicators: dict) -> float:
        """Score based on volume patterns."""
        score = 0.0
        trend = vol_data.get("volume_trend", "stable")
        divergence = vol_data.get("price_volume_divergence", False)

        # Check if uptrend with increasing volume
        ma5 = self._last_valid(indicators.get("ma", {}).get("ma5", []))
        ma20 = self._last_valid(indicators.get("ma", {}).get("ma20", []))

        if ma5 is not None and ma20 is not None:
            in_uptrend = ma5 > ma20
            if in_uptrend and trend == "increasing":
                score += 10  # volume confirms uptrend
            elif in_uptrend and trend == "decreasing":
                score -= 5  # volume diverges from uptrend
            elif not in_uptrend and trend == "increasing":
                score -= 5  # selling pressure increasing

        if divergence:
            score -= 5

        return score

    # --- Summary generation ---

    def _generate_summary(
        self,
        score: float,
        indicators: dict,
        signals: list[dict],
    ) -> str:
        """Generate a brief Chinese summary of the technical analysis."""
        # Determine trend description
        if score >= 50:
            trend_desc = "技術面強勢多頭"
        elif score >= 20:
            trend_desc = "技術面偏多"
        elif score >= -20:
            trend_desc = "技術面中性整理"
        elif score >= -50:
            trend_desc = "技術面偏空"
        else:
            trend_desc = "技術面弱勢空頭"

        parts = [f"【技術評分 {score:+.0f}】{trend_desc}。"]

        # MA status
        ma_data = indicators.get("ma", {})
        ma5 = self._last_valid(ma_data.get("ma5", []))
        ma20 = self._last_valid(ma_data.get("ma20", []))
        if ma5 is not None and ma20 is not None:
            if ma5 > ma20:
                parts.append("短期均線在長期均線之上，短線走勢偏強。")
            else:
                parts.append("短期均線在長期均線之下，短線走勢偏弱。")

        # RSI status
        rsi_data = indicators.get("rsi", [])
        if rsi_data:
            rsi = rsi_data[-1]
            if rsi > 70:
                parts.append(f"RSI {rsi:.0f} 已進入超買區域，注意回檔風險。")
            elif rsi < 30:
                parts.append(f"RSI {rsi:.0f} 已進入超賣區域，留意反彈契機。")

        # Signal summary
        bullish = [s for s in signals if s["direction"] == "bullish"]
        bearish = [s for s in signals if s["direction"] == "bearish"]
        if bullish:
            parts.append(f"偵測到 {len(bullish)} 個多頭訊號。")
        if bearish:
            parts.append(f"偵測到 {len(bearish)} 個空頭訊號。")

        if not bullish and not bearish:
            parts.append("目前無明顯買賣訊號。")

        return "".join(parts)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

technical_service = TechnicalService()
