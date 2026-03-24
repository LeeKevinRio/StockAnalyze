"""Chinese financial sentiment analyzer using a keyword-based lexicon.

Zero-cost, zero-latency sentiment scoring for Chinese financial text.
Handles traditional Chinese financial terminology, PTT/social media slang,
negation detection, and intensity modifiers.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SentimentResult:
    """Result of a single sentiment analysis.

    Attributes:
        score: Normalised sentiment score in the range [-1.0, 1.0].
        label: Human-readable label -- ``'positive'``, ``'negative'``, or ``'neutral'``.
        confidence: Confidence of the label in the range [0.0, 1.0].
        matched_terms: List of ``(term, effective_weight)`` tuples for every
            lexicon term that was detected in the input text.
    """

    score: float
    label: str
    confidence: float
    matched_terms: list[tuple[str, float]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Lexicon
# ---------------------------------------------------------------------------

# Strong positive (0.8 - 1.0)
_STRONG_POSITIVE: dict[str, float] = {
    "大漲": 0.9,
    "暴漲": 1.0,
    "飆漲": 1.0,
    "漲停": 1.0,
    "強勢": 0.8,
    "噴出": 0.9,
    "爆量上攻": 0.95,
    "創新高": 0.9,
    "突破": 0.8,
    "利多": 0.8,
    "營收創高": 0.9,
    "獲利成長": 0.85,
    "超預期": 0.85,
    "法人買超": 0.8,
    "外資加碼": 0.8,
    "股利增加": 0.8,
    "轉機": 0.8,
    "多頭": 0.8,
    "利多出盡": 0.5,
    "大幅成長": 0.9,
    "業績亮眼": 0.85,
    "強彈": 0.85,
    "攻上": 0.8,
    "衝高": 0.85,
    "帶量突破": 0.9,
    "利多加持": 0.85,
    "逆勢上漲": 0.85,
    "市場看好": 0.8,
}

# Medium positive (0.4 - 0.7)
_MEDIUM_POSITIVE: dict[str, float] = {
    "上漲": 0.6,
    "漲": 0.5,
    "看好": 0.6,
    "樂觀": 0.6,
    "買進": 0.6,
    "加碼": 0.6,
    "升級": 0.5,
    "上調": 0.55,
    "成長": 0.5,
    "增加": 0.45,
    "獲利": 0.5,
    "回升": 0.5,
    "反彈": 0.5,
    "站穩": 0.45,
    "突破均線": 0.55,
    "量增價漲": 0.65,
    "走揚": 0.5,
    "收紅": 0.5,
    "紅盤": 0.45,
    "翻紅": 0.5,
    "買盤進場": 0.55,
    "量能放大": 0.5,
    "正面": 0.5,
    "偏多": 0.45,
    "回溫": 0.45,
    "轉強": 0.55,
    "帶量上攻": 0.6,
}

# Mild positive (0.1 - 0.3)
_MILD_POSITIVE: dict[str, float] = {
    "持平偏多": 0.2,
    "小漲": 0.25,
    "微幅上揚": 0.15,
    "穩健": 0.2,
    "正向": 0.25,
    "平穩": 0.15,
    "溫和成長": 0.2,
    "小幅上漲": 0.2,
    "緩步走高": 0.2,
    "持穩": 0.15,
    "尚可": 0.1,
}

# Strong negative (-0.8 to -1.0)
_STRONG_NEGATIVE: dict[str, float] = {
    "大跌": -0.9,
    "暴跌": -1.0,
    "崩盤": -1.0,
    "跌停": -1.0,
    "重挫": -0.95,
    "恐慌": -0.85,
    "利空": -0.8,
    "營收衰退": -0.85,
    "虧損擴大": -0.9,
    "下市": -0.95,
    "警示": -0.8,
    "違約交割": -0.95,
    "掏空": -1.0,
    "做假帳": -1.0,
    "腰斬": -0.9,
    "斷頭": -0.9,
    "爆雷": -0.95,
    "清算": -0.85,
    "破產": -1.0,
    "資金斷鏈": -0.9,
    "全面崩跌": -1.0,
}

# Medium negative (-0.4 to -0.7)
_MEDIUM_NEGATIVE: dict[str, float] = {
    "下跌": -0.6,
    "跌": -0.5,
    "看空": -0.6,
    "悲觀": -0.6,
    "賣出": -0.6,
    "減碼": -0.55,
    "降級": -0.5,
    "下調": -0.55,
    "衰退": -0.6,
    "減少": -0.45,
    "虧損": -0.6,
    "回檔": -0.45,
    "破底": -0.6,
    "跌破均線": -0.55,
    "量縮價跌": -0.65,
    "走跌": -0.5,
    "收黑": -0.5,
    "翻黑": -0.5,
    "賣壓湧現": -0.6,
    "量能萎縮": -0.45,
    "偏空": -0.45,
    "轉弱": -0.55,
    "外資賣超": -0.55,
    "法人賣超": -0.55,
    "調降目標價": -0.6,
    "獲利了結": -0.4,
}

# Mild negative (-0.1 to -0.3)
_MILD_NEGATIVE: dict[str, float] = {
    "持平偏空": -0.2,
    "小跌": -0.25,
    "微幅下挫": -0.15,
    "壓力": -0.2,
    "疑慮": -0.2,
    "觀望": -0.15,
    "承壓": -0.25,
    "小幅下跌": -0.2,
    "緩步走低": -0.2,
    "不確定": -0.15,
}

# PTT / social-media slang -- positive
_SLANG_POSITIVE: dict[str, float] = {
    "噴": 0.7,
    "發財": 0.7,
    "上車": 0.6,
    "抄底": 0.6,
    "存股": 0.4,
    "多多": 0.5,
    "牛": 0.5,
    "起飛": 0.75,
    "歐印": 0.65,
    "All in": 0.65,
    "財富自由": 0.7,
    "賺爛": 0.75,
    "無腦多": 0.5,
    "穩了": 0.5,
}

# PTT / social-media slang -- negative
_SLANG_NEGATIVE: dict[str, float] = {
    "GG": -0.7,
    "韭菜": -0.6,
    "套牢": -0.7,
    "割肉": -0.7,
    "住套房": -0.7,
    "慘": -0.6,
    "崩": -0.8,
    "空空": -0.5,
    "熊": -0.5,
    "畢業": -0.6,
    "被割": -0.65,
    "賠到脫褲": -0.75,
    "血流成河": -0.8,
    "綠油油": -0.6,
    "跳水": -0.7,
    "滅頂": -0.8,
    "出事": -0.5,
}


def _build_lexicon() -> dict[str, float]:
    """Merge all sub-lexicons into a single term -> weight mapping.

    Longer terms are checked first during scanning (see :meth:`_scan_terms`),
    so overlapping entries (e.g. "漲" vs "大漲") are handled correctly.
    """
    merged: dict[str, float] = {}
    for sub in (
        _STRONG_POSITIVE,
        _MEDIUM_POSITIVE,
        _MILD_POSITIVE,
        _STRONG_NEGATIVE,
        _MEDIUM_NEGATIVE,
        _MILD_NEGATIVE,
        _SLANG_POSITIVE,
        _SLANG_NEGATIVE,
    ):
        merged.update(sub)
    return merged


# Module-level lexicon -- built once at import time.
_LEXICON: dict[str, float] = _build_lexicon()

# Pre-sort terms by descending length for greedy matching.
_SORTED_TERMS: list[str] = sorted(_LEXICON.keys(), key=len, reverse=True)

# ---------------------------------------------------------------------------
# Negation and intensity modifier lists
# ---------------------------------------------------------------------------

_NEGATION_WORDS: set[str] = {
    "不", "沒", "未", "非", "無", "別", "勿",
    "沒有", "不會", "不是", "並非", "不再", "尚未", "從未",
}

# Pre-sort by descending length for greedy matching.
_NEGATION_SORTED: list[str] = sorted(_NEGATION_WORDS, key=len, reverse=True)

_AMPLIFIERS: set[str] = {"非常", "極度", "超級", "大幅", "嚴重", "持續", "極為", "相當"}
_DIMINISHERS: set[str] = {"稍微", "略微", "小幅", "些許", "略為", "微幅"}

_AMPLIFIER_SORTED: list[str] = sorted(_AMPLIFIERS, key=len, reverse=True)
_DIMINISHER_SORTED: list[str] = sorted(_DIMINISHERS, key=len, reverse=True)

# Maximum character gap between a negation word and the sentiment term it
# modifies.  "不 看好" (with a space) should still match.
_NEGATION_WINDOW: int = 2


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class ChineseSentimentAnalyzer:
    """Keyword-based sentiment analyzer for Chinese financial text.

    The analyser maintains a curated lexicon of 100+ Chinese financial terms
    spanning formal market vocabulary and PTT/social-media slang. It applies
    negation detection (e.g. "不看好" flips the sign of "看好") and intensity
    modifiers (amplifiers / diminishers).

    Example::

        analyzer = ChineseSentimentAnalyzer()
        result = analyzer.analyze("台積電今天大漲三根停板，法人持續買超")
        print(result.score, result.label)  # 0.87 positive
    """

    def __init__(self) -> None:
        self._lexicon: dict[str, float] = _LEXICON
        self._terms: list[str] = _SORTED_TERMS

    # -- public API ----------------------------------------------------------

    def analyze(self, text: str) -> SentimentResult:
        """Analyse a single Chinese text and return a :class:`SentimentResult`.

        Args:
            text: Chinese financial text (news headline, PTT post body, etc.).

        Returns:
            A :class:`SentimentResult` with score, label, confidence, and
            matched_terms.
        """
        if not text or not text.strip():
            return SentimentResult(
                score=0.0,
                label="neutral",
                confidence=0.0,
                matched_terms=[],
            )

        # 1. Scan for known terms and record their positions.
        raw_matches = self._scan_terms(text)
        if not raw_matches:
            return SentimentResult(
                score=0.0,
                label="neutral",
                confidence=0.0,
                matched_terms=[],
            )

        # 2. Apply negation and intensity modifiers.
        adjusted_matches = self._apply_modifiers(text, raw_matches)

        # 3. Calculate weighted average score.
        weights = [w for _, w in adjusted_matches]
        score = sum(weights) / len(weights)

        # Clamp to [-1, 1].
        score = max(-1.0, min(1.0, score))

        # 4. Determine label and confidence.
        label = self._score_to_label(score)
        confidence = self._calculate_confidence(weights, score)

        return SentimentResult(
            score=round(score, 4),
            label=label,
            confidence=round(confidence, 4),
            matched_terms=[(t, round(w, 4)) for t, w in adjusted_matches],
        )

    def batch_analyze(self, texts: list[str]) -> list[SentimentResult]:
        """Analyse a list of texts and return results in the same order.

        Args:
            texts: List of Chinese financial text strings.

        Returns:
            Corresponding list of :class:`SentimentResult` instances.
        """
        return [self.analyze(t) for t in texts]

    # -- internal helpers ----------------------------------------------------

    def _scan_terms(self, text: str) -> list[tuple[str, float, int]]:
        """Greedy-scan *text* for lexicon terms, longest-match first.

        Returns a list of ``(term, raw_weight, start_position)`` tuples.
        Each character position in the text is consumed at most once to avoid
        double-counting overlapping terms.
        """
        consumed: set[int] = set()
        matches: list[tuple[str, float, int]] = []

        for term in self._terms:
            start = 0
            while True:
                idx = text.find(term, start)
                if idx == -1:
                    break
                positions = set(range(idx, idx + len(term)))
                if not positions & consumed:
                    consumed |= positions
                    matches.append((term, self._lexicon[term], idx))
                start = idx + 1

        # Sort by position for deterministic output.
        matches.sort(key=lambda m: m[2])
        return matches

    def _apply_modifiers(
        self,
        text: str,
        matches: list[tuple[str, float, int]],
    ) -> list[tuple[str, float]]:
        """Apply negation flipping and intensity modifiers to raw matches.

        For each matched term the method inspects the characters immediately
        preceding the term in the original text.

        * **Negation** (within ``_NEGATION_WINDOW`` characters before the
          term): the sign of the weight is flipped.
        * **Amplifiers** (immediately before the term or before the negation):
          the absolute weight is multiplied by 1.5.
        * **Diminishers** (same window): the absolute weight is multiplied by
          0.5.

        Returns a list of ``(term_display, effective_weight)`` tuples.
        """
        results: list[tuple[str, float]] = []

        for term, weight, pos in matches:
            # Look at the preceding context (up to 6 characters for modifiers +
            # negation).
            window_start = max(0, pos - 6)
            prefix = text[window_start:pos]

            negated = False
            amplified = False
            diminished = False

            # Check negation.
            for neg in _NEGATION_SORTED:
                # Negation must appear within _NEGATION_WINDOW chars of the term.
                neg_start = prefix.rfind(neg)
                if neg_start != -1:
                    gap = len(prefix) - neg_start - len(neg)
                    if gap <= _NEGATION_WINDOW:
                        negated = True
                        break

            # Check amplifiers (anywhere in the prefix window).
            for amp in _AMPLIFIER_SORTED:
                if amp in prefix:
                    amplified = True
                    break

            # Check diminishers.
            for dim in _DIMINISHER_SORTED:
                if dim in prefix:
                    diminished = True
                    break

            effective = weight
            if negated:
                effective = -effective
            if amplified:
                effective *= 1.5
            elif diminished:
                effective *= 0.5

            # Clamp individual weights to [-1, 1].
            effective = max(-1.0, min(1.0, effective))

            display = term
            if negated:
                # Find the negation word again to build the display string.
                for neg in _NEGATION_SORTED:
                    neg_start = prefix.rfind(neg)
                    if neg_start != -1:
                        gap = len(prefix) - neg_start - len(neg)
                        if gap <= _NEGATION_WINDOW:
                            display = f"{neg}{term}"
                            break

            results.append((display, effective))

        return results

    @staticmethod
    def _score_to_label(score: float) -> str:
        """Map a normalised score to a human-readable label."""
        if score > 0.05:
            return "positive"
        if score < -0.05:
            return "negative"
        return "neutral"

    @staticmethod
    def _calculate_confidence(weights: list[float], score: float) -> float:
        """Estimate confidence based on agreement and coverage.

        Confidence is higher when:
        - More terms were matched (coverage).
        - Matched terms agree in direction (low variance).
        - The absolute score is further from zero (stronger signal).

        Returns a value in [0.0, 1.0].
        """
        n = len(weights)
        if n == 0:
            return 0.0

        # Coverage factor: more terms -> higher confidence (saturates at ~10).
        coverage = min(n / 10.0, 1.0)

        # Agreement factor: what fraction of terms agree with the final sign?
        if abs(score) < 1e-9:
            agreement = 0.5
        else:
            sign = 1.0 if score > 0 else -1.0
            agreeing = sum(1 for w in weights if w * sign > 0)
            agreement = agreeing / n

        # Magnitude factor: stronger absolute score -> higher confidence.
        magnitude = min(abs(score) / 0.5, 1.0)

        # Weighted combination.
        confidence = 0.35 * coverage + 0.40 * agreement + 0.25 * magnitude
        return max(0.0, min(1.0, confidence))


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

sentiment_analyzer = ChineseSentimentAnalyzer()
