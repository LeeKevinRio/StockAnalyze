"""Unit tests for the report generator's structured-output parsing."""

from app.services.report_generator import ReportGenerator

gen = ReportGenerator()

SAMPLE = """## 一、消息面分析
台積電近期消息偏多。

## 六、綜合評估與建議
- 目標價位: 2600 元

```json
{"target_price": 2600, "stop_loss_price": 2300.5, "risk_level": "medium",
 "short_term_outlook": "短期技術面偏多，若站穩 2500 可續抱，跌破 2400 停損離場，預期兩週內挑戰 2600。",
 "medium_term_outlook": "中期受惠 AI 需求，2450-2650 區間操作，回檔至月線分批佈局。",
 "long_term_outlook": "長期產業趨勢向上，目標 2800，適合定期定額長線持有。"}
```
"""


def test_parse_json_block():
    meta = gen._parse_json_block(SAMPLE)
    assert meta["target_price"] == 2600
    assert meta["stop_loss_price"] == 2300.5
    assert meta["risk_level"] == "medium"
    assert "2600" in meta["short_term_outlook"]


def test_parse_json_block_missing():
    assert gen._parse_json_block("## 報告\n沒有 JSON 區塊") == {}


def test_parse_json_block_malformed():
    assert gen._parse_json_block("```json\n{broken json}\n```") == {}


def test_strip_json_block():
    stripped = gen._strip_json_block(SAMPLE)
    assert "```json" not in stripped
    assert "消息面分析" in stripped
    assert "目標價位: 2600" in stripped


def test_num_coercion():
    assert gen._num(2600) == 2600.0
    assert gen._num("2300.5") == 2300.5
    assert gen._num(None) is None
    assert gen._num("N/A") is None
    assert gen._num(-5) is None
    assert gen._num(0) is None
