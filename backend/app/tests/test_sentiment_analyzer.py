"""Unit tests for the Chinese financial sentiment analyzer."""

import pytest
from app.services.sentiment_analyzer import sentiment_analyzer, ChineseSentimentAnalyzer


class TestChineseSentimentAnalyzer:
    def setup_method(self):
        self.analyzer = ChineseSentimentAnalyzer()

    def test_strong_positive(self):
        result = self.analyzer.analyze("台積電今天大漲，股價創新高")
        assert result.score > 0.3
        assert result.label == "positive"

    def test_strong_negative(self):
        result = self.analyzer.analyze("股價暴跌崩盤，投資人恐慌賣出")
        assert result.score < -0.3
        assert result.label == "negative"

    def test_neutral(self):
        result = self.analyzer.analyze("今天天氣不錯")
        assert -0.2 <= result.score <= 0.2
        assert result.label == "neutral"

    def test_negation_handling(self):
        result = self.analyzer.analyze("分析師不看好後市")
        assert result.score < 0  # "不看好" should be negative

    def test_ptt_slang_positive(self):
        result = self.analyzer.analyze("這支股票要噴了，趕快上車")
        assert result.score > 0

    def test_ptt_slang_negative(self):
        result = self.analyzer.analyze("又套牢了，變韭菜")
        assert result.score < 0

    def test_mixed_sentiment(self):
        result = self.analyzer.analyze("雖然營收成長，但毛利率下降令人擔憂")
        # Mixed - should not be strongly positive or negative
        assert -0.5 <= result.score <= 0.5

    def test_empty_text(self):
        result = self.analyzer.analyze("")
        assert result.score == 0
        assert result.label == "neutral"

    def test_batch_analyze(self):
        texts = ["大漲", "暴跌", "平穩"]
        results = self.analyzer.batch_analyze(texts)
        assert len(results) == 3
        assert results[0].score > 0
        assert results[1].score < 0

    def test_intensity_amplifier(self):
        mild = self.analyzer.analyze("上漲")
        strong = self.analyzer.analyze("大幅上漲")
        assert strong.score >= mild.score  # Amplifier should increase magnitude

    def test_singleton_exists(self):
        assert sentiment_analyzer is not None
