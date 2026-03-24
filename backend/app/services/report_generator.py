"""AI report generator — produces comprehensive analysis reports using LLM.

Takes the structured AnalysisResult from the analysis engine and generates
a detailed, multi-section report in Traditional Chinese using the configured
LLM provider.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analysis_engine import AnalysisResult
from app.services.llm_service import llm_service, LLMError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ReportOutput:
    """Structured output from the AI report generator."""

    markdown: str = ""
    provider: str = ""
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    risk_level: str = "MEDIUM"
    short_term_outlook: str = ""
    medium_term_outlook: str = ""
    long_term_outlook: str = ""


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class ReportGenerator:
    """Generate comprehensive AI analysis reports using LLM."""

    SYSTEM_PROMPT = (
        "你是一位資深台灣股票研究分析師，正在撰寫一份詳盡的個股分析報告。\n"
        "請使用繁體中文，以專業但易懂的語言撰寫。\n"
        "報告結構必須包含以下章節，消息面為最重要的分析維度，需要最詳細的分析。\n"
        "所有數字引用請保持精確，不要捏造數據。若資料不足請明確說明。\n"
        "請勿使用 emoji 符號。"
    )

    async def generate_report(
        self,
        stock_id: str,
        stock_name: str,
        analysis: AnalysisResult,
        db: AsyncSession = None,
    ) -> ReportOutput:
        """Generate full analysis report.

        Steps:
        1. Build structured data prompt with all analysis data
        2. Add pre-computed scores to guide LLM direction
        3. Call LLM with system prompt + data prompt
        4. Parse and validate output
        5. Extract target price and stop-loss from LLM output
        6. Return structured report

        Args:
            stock_id: Taiwan stock ID.
            stock_name: Stock display name.
            analysis: AnalysisResult from the analysis engine.
            db: Optional database session for LLM usage logging.

        Returns:
            ReportOutput with the markdown report and extracted fields.
        """
        output = ReportOutput()

        # Build prompts
        data_context = self._build_data_prompt(stock_id, stock_name, analysis)
        full_prompt = self._build_report_prompt(data_context, analysis)

        try:
            # Call LLM
            report_text = await llm_service.call(
                prompt=full_prompt,
                system_prompt=self.SYSTEM_PROMPT,
                temperature=0.4,
                output_format="text",
                max_tokens=8192,
                purpose="analysis_report",
                db=db,
            )

            # Determine which provider was used
            providers = llm_service.available_providers
            output.provider = providers[0] if providers else "unknown"

            output.markdown = report_text

            # Extract structured data from the report
            output.target_price = self._extract_target_price(report_text)
            output.stop_loss_price = self._extract_stop_loss(report_text)
            output.risk_level = self._extract_risk_level(report_text)

            outlooks = self._extract_outlooks(report_text)
            output.short_term_outlook = outlooks.get("short", "")
            output.medium_term_outlook = outlooks.get("medium", "")
            output.long_term_outlook = outlooks.get("long", "")

            logger.info(
                "Generated AI report for %s (%s): %d chars, provider=%s",
                stock_id,
                stock_name,
                len(report_text),
                output.provider,
            )

        except LLMError as exc:
            logger.error("Failed to generate AI report for %s: %s", stock_id, exc)
            output.markdown = self._build_fallback_report(stock_id, stock_name, analysis)
            output.provider = "fallback"
            output.risk_level = self._infer_risk_from_score(analysis.overall_score)

        return output

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    def _build_data_prompt(
        self, stock_id: str, stock_name: str, analysis: AnalysisResult
    ) -> str:
        """Build the data context prompt with all collected data.

        Includes stock basic info, latest price, news data, social data,
        fundamental data, technical data, institutional data, macro data,
        and pre-computed dimension scores.

        Args:
            stock_id: Taiwan stock ID.
            stock_name: Stock display name.
            analysis: AnalysisResult with all raw data.

        Returns:
            Formatted data context string.
        """
        lines = []
        raw = analysis.raw_data
        details = analysis.dimension_details

        # Stock basic info
        lines.append(f"## 個股基本資訊")
        lines.append(f"- 股票代號: {stock_id}")
        lines.append(f"- 股票名稱: {stock_name}")

        # Latest price
        prices = raw.get("prices", [])
        if prices:
            latest = prices[-1]
            lines.append(f"- 最新收盤價: {latest.get('close', 'N/A')}")
            lines.append(f"- 最新成交量: {latest.get('volume', 'N/A')}")
            if len(prices) >= 2:
                prev = prices[-2]
                if latest.get("close") and prev.get("close") and prev["close"] != 0:
                    change_pct = (latest["close"] - prev["close"]) / prev["close"] * 100
                    lines.append(f"- 漲跌幅: {change_pct:+.2f}%")

        # Fundamentals
        fund = raw.get("fundamentals", {})
        if fund:
            lines.append("")
            lines.append("## 基本面數據")
            if fund.get("pe_ratio"):
                lines.append(f"- 本益比 (PE): {fund['pe_ratio']:.2f}")
            if fund.get("pb_ratio"):
                lines.append(f"- 股價淨值比 (PB): {fund['pb_ratio']:.2f}")
            if fund.get("eps"):
                lines.append(f"- 每股盈餘 (EPS): {fund['eps']:.2f}")
            if fund.get("roe"):
                lines.append(f"- 股東權益報酬率 (ROE): {fund['roe']:.1f}%")
            if fund.get("gross_margin"):
                lines.append(f"- 毛利率: {fund['gross_margin']:.1f}%")
            if fund.get("operating_margin"):
                lines.append(f"- 營業利益率: {fund['operating_margin']:.1f}%")
            if fund.get("net_margin"):
                lines.append(f"- 淨利率: {fund['net_margin']:.1f}%")
            if fund.get("revenue"):
                lines.append(f"- 營收: {fund['revenue']:,.0f}")
            if fund.get("market_cap"):
                lines.append(f"- 市值: {fund['market_cap']:,.0f}")

        # Fundamental growth details
        fund_detail = details.get("fundamental", {})
        if fund_detail.get("available"):
            if fund_detail.get("eps_growth_yoy") is not None:
                lines.append(f"- EPS 年增率: {fund_detail['eps_growth_yoy']:.1f}%")
            if fund_detail.get("revenue_growth_yoy") is not None:
                lines.append(f"- 營收年增率: {fund_detail['revenue_growth_yoy']:.1f}%")
            if fund_detail.get("industry_pe_avg") is not None:
                lines.append(f"- 產業平均本益比: {fund_detail['industry_pe_avg']:.1f}")

        # Dividends
        dividends = raw.get("dividends", [])
        if dividends:
            lines.append("")
            lines.append("## 股利資訊")
            for d in dividends[:3]:
                cash = d.get("cash_dividend", 0) or 0
                stock_div = d.get("stock_dividend", 0) or 0
                dy = d.get("dividend_yield")
                dy_str = f"，殖利率 {dy:.1f}%" if dy else ""
                lines.append(f"- {d.get('year', 'N/A')}年: 現金股利 {cash:.2f}，股票股利 {stock_div:.2f}{dy_str}")

        # News data
        news = raw.get("news", [])
        if news:
            lines.append("")
            lines.append("## 近期新聞")
            for n in news[:10]:
                sentiment = n.get("sentiment", "neutral")
                score = n.get("sentiment_score")
                score_str = f" (情緒分數: {score:.2f})" if score is not None else ""
                impact = n.get("impact_level", "")
                impact_str = f" [影響力: {impact}]" if impact else ""
                lines.append(f"- [{sentiment}]{impact_str} {n.get('title', '')}{score_str}")

        # Social / sentiment summary
        sentiment = raw.get("sentiment", {})
        if sentiment and sentiment.get("combined_score") is not None:
            lines.append("")
            lines.append("## 社群情緒")
            lines.append(f"- 綜合情緒分數: {sentiment.get('combined_score', 'N/A')}")
            lines.append(f"- 提及次數: {sentiment.get('mention_count', 0)}")
            lines.append(f"- 正面/負面/中性: {sentiment.get('positive_count', 0)}/{sentiment.get('negative_count', 0)}/{sentiment.get('neutral_count', 0)}")
            lines.append(f"- 熱度: {sentiment.get('heat_level', 'N/A')}")

        # Technical details
        tech_detail = details.get("technical", {})
        if tech_detail.get("available"):
            lines.append("")
            lines.append("## 技術面數據")
            indicators = tech_detail.get("indicators", {})

            ma = indicators.get("ma", {})
            if ma:
                for period, val in ma.items():
                    if val is not None:
                        lines.append(f"- MA{period}: {val:.2f}")

            macd = indicators.get("macd", {})
            if macd:
                lines.append(f"- MACD: {macd.get('macd', 'N/A')}, Signal: {macd.get('signal', 'N/A')}")

            rsi = indicators.get("rsi", {})
            if rsi:
                for period, val in rsi.items():
                    if val is not None:
                        lines.append(f"- RSI{period}: {val:.1f}")

            kd = indicators.get("kd", {})
            if kd:
                lines.append(f"- K值: {kd.get('k', 'N/A')}, D值: {kd.get('d', 'N/A')}")

            signals = tech_detail.get("signals", [])
            if signals:
                lines.append("- 技術訊號:")
                for sig in signals[:5]:
                    if isinstance(sig, dict):
                        lines.append(f"  - {sig.get('description', sig.get('signal_type', 'N/A'))}")

        # Institutional details
        inst_detail = details.get("institutional", {})
        if inst_detail.get("available"):
            lines.append("")
            lines.append("## 籌碼面數據")
            lines.append(f"- 外資趨勢: {inst_detail.get('foreign_trend', 'N/A')}")
            lines.append(f"- 投信趨勢: {inst_detail.get('trust_trend', 'N/A')}")
            lines.append(f"- 自營商趨勢: {inst_detail.get('dealer_trend', 'N/A')}")
            lines.append(f"- 外資連續買賣天數: {inst_detail.get('foreign_consecutive_days', 0)}")
            lines.append(f"- 外資20日累計: {inst_detail.get('cumulative_foreign_20d', 0):,}")
            lines.append(f"- 投信20日累計: {inst_detail.get('cumulative_trust_20d', 0):,}")
            lines.append(f"- 融資趨勢: {inst_detail.get('margin_trend', 'N/A')}")
            lines.append(f"- 融券趨勢: {inst_detail.get('short_trend', 'N/A')}")
            lines.append(f"- 軋空潛力: {'是' if inst_detail.get('squeeze_potential') else '否'}")

        # Macro details
        macro_detail = details.get("macro", {})
        if macro_detail.get("available"):
            lines.append("")
            lines.append("## 總體經濟環境")
            lines.append(f"- 利率循環: {macro_detail.get('rate_cycle', 'N/A')}")
            lines.append(f"- 景氣循環: {macro_detail.get('business_cycle', 'N/A')}")
            lines.append(f"- 加權指數趨勢: {macro_detail.get('taiex_trend', 'N/A')}")
            lines.append(f"- VIX 水準: {macro_detail.get('vix_level', 'N/A')}")

        # Pre-computed scores
        lines.append("")
        lines.append("## 各維度評分 (系統計算)")
        lines.append(f"- 消息面分數: {analysis.scores.get('news', 0):.1f}")
        lines.append(f"- 基本面分數: {analysis.scores.get('fundamental', 0):.1f}")
        lines.append(f"- 技術面分數: {analysis.scores.get('technical', 0):.1f}")
        lines.append(f"- 籌碼面分數: {analysis.scores.get('institutional', 0):.1f}")
        lines.append(f"- 總經面分數: {analysis.scores.get('macro', 0):.1f}")
        lines.append(f"- 綜合評分: {analysis.overall_score:.1f}")
        lines.append(f"- 綜合訊號: {analysis.overall_signal}")
        lines.append(f"- 信心度: {analysis.confidence:.2f}")
        lines.append(f"- 市場體制: {analysis.regime}")

        return "\n".join(lines)

    def _build_report_prompt(
        self, data_context: str, analysis: AnalysisResult
    ) -> str:
        """Build the report generation prompt.

        Constructs the full prompt combining data context with specific
        output format requirements.

        Args:
            data_context: The formatted data context string.
            analysis: AnalysisResult for signal guidance.

        Returns:
            Complete prompt string for LLM generation.
        """
        signal_map = {
            "strong_buy": "強力買進",
            "buy": "買進",
            "neutral": "持有/觀望",
            "sell": "賣出",
            "strong_sell": "強力賣出",
        }
        signal_zh = signal_map.get(analysis.overall_signal, "觀望")

        prompt = f"""根據以下分析數據，撰寫一份完整的個股分析報告。

{data_context}

---

請依照以下結構撰寫報告（使用 Markdown 格式）：

## 一、消息面分析（最重要，需最詳細 300+ 字）
- 近期重要新聞及其影響
- 社群媒體情緒分析
- 產業趨勢影響
- 消息面風險因素

## 二、基本面分析（200+ 字）
- 營收與獲利趨勢
- 估值水平評估
- 同業比較
- 財務健康度

## 三、技術面分析（200+ 字）
- 趨勢判斷
- 關鍵指標信號
- 支撐與壓力位
- 量價分析

## 四、籌碼面分析（200+ 字）
- 三大法人動向
- 融資融券變化
- 籌碼集中度

## 五、總體經濟面分析（150+ 字）
- 利率環境影響
- 匯率影響
- 景氣循環位置

## 六、綜合評估與建議
基於系統計算的綜合評分 {analysis.overall_score:.1f} 分及各維度分析結果，系統建議方向為「{signal_zh}」。請給出你的專業判斷：

- 整體評級: {{BUY/SELL/HOLD}}（請參考系統建議但給出你的判斷）
- 信心度: {{0.0-1.0}}
- 風險等級: {{HIGH/MEDIUM/LOW}}
- 短期展望 (1-2週): ...
- 中期展望 (1-3月): ...
- 長期展望 (3-12月): ...
- 建議進場區間: ...
- 停損價位: ...
- 目標價位: ...

注意：
1. 如果某個維度資料不足，請明確說明「資料不足，無法進行深入分析」
2. 不要捏造或編造不存在的數據
3. 報告中的所有數字須與提供的數據一致
4. 建議進場區間、停損和目標價位請基於現有數據合理推估
"""
        return prompt

    # ------------------------------------------------------------------
    # Extraction methods
    # ------------------------------------------------------------------

    def _extract_target_price(self, report_text: str) -> Optional[float]:
        """Extract target price from the report text using regex.

        Searches for patterns like '目標價位: 150' or '目標價: 150.5'.

        Args:
            report_text: The generated report markdown.

        Returns:
            Target price as float, or None if not found.
        """
        patterns = [
            r"目標價位[：:]\s*(?:約?\s*)?(\d+(?:\.\d+)?)",
            r"目標價[：:]\s*(?:約?\s*)?(\d+(?:\.\d+)?)",
            r"目標價位\s*(?:約?\s*)(\d+(?:\.\d+)?)\s*[元]",
            r"目標價\s*(?:約?\s*)(\d+(?:\.\d+)?)\s*[元]",
            r"target.*?(\d+(?:\.\d+)?)",
        ]
        return self._extract_price(report_text, patterns)

    def _extract_stop_loss(self, report_text: str) -> Optional[float]:
        """Extract stop-loss price from the report text.

        Args:
            report_text: The generated report markdown.

        Returns:
            Stop-loss price as float, or None if not found.
        """
        patterns = [
            r"停損價位[：:]\s*(?:約?\s*)?(\d+(?:\.\d+)?)",
            r"停損[：:]\s*(?:約?\s*)?(\d+(?:\.\d+)?)",
            r"停損價位\s*(?:約?\s*)(\d+(?:\.\d+)?)\s*[元]",
            r"停損價\s*(?:約?\s*)(\d+(?:\.\d+)?)\s*[元]",
            r"stop.?loss.*?(\d+(?:\.\d+)?)",
        ]
        return self._extract_price(report_text, patterns)

    @staticmethod
    def _extract_price(text: str, patterns: list[str]) -> Optional[float]:
        """Try multiple regex patterns to extract a price value."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    if value > 0:
                        return value
                except (ValueError, IndexError):
                    continue
        return None

    def _extract_risk_level(self, report_text: str) -> str:
        """Extract risk level from report.

        Args:
            report_text: The generated report markdown.

        Returns:
            One of 'HIGH', 'MEDIUM', 'LOW'.
        """
        patterns = [
            r"風險等級[：:]\s*(HIGH|MEDIUM|LOW|高|中|低)",
            r"risk.*?level[：:]\s*(HIGH|MEDIUM|LOW)",
        ]
        for pattern in patterns:
            match = re.search(pattern, report_text, re.IGNORECASE)
            if match:
                level = match.group(1).upper()
                level_map = {"高": "HIGH", "中": "MEDIUM", "低": "LOW"}
                return level_map.get(level, level)

        return "MEDIUM"

    def _extract_outlooks(self, report_text: str) -> dict:
        """Extract short/medium/long term outlooks from report.

        Args:
            report_text: The generated report markdown.

        Returns:
            Dict with keys 'short', 'medium', 'long'.
        """
        outlooks = {"short": "", "medium": "", "long": ""}

        # Short term
        short_patterns = [
            r"短期展望[^：:]*[：:]\s*(.+?)(?:\n|$)",
            r"短期\s*\(1-2週?\)[：:]\s*(.+?)(?:\n|$)",
        ]
        for pattern in short_patterns:
            match = re.search(pattern, report_text)
            if match:
                outlooks["short"] = match.group(1).strip()
                break

        # Medium term
        medium_patterns = [
            r"中期展望[^：:]*[：:]\s*(.+?)(?:\n|$)",
            r"中期\s*\(1-3月?\)[：:]\s*(.+?)(?:\n|$)",
        ]
        for pattern in medium_patterns:
            match = re.search(pattern, report_text)
            if match:
                outlooks["medium"] = match.group(1).strip()
                break

        # Long term
        long_patterns = [
            r"長期展望[^：:]*[：:]\s*(.+?)(?:\n|$)",
            r"長期\s*\(3-12月?\)[：:]\s*(.+?)(?:\n|$)",
        ]
        for pattern in long_patterns:
            match = re.search(pattern, report_text)
            if match:
                outlooks["long"] = match.group(1).strip()
                break

        return outlooks

    # ------------------------------------------------------------------
    # Fallback report
    # ------------------------------------------------------------------

    @staticmethod
    def _build_fallback_report(
        stock_id: str, stock_name: str, analysis: AnalysisResult
    ) -> str:
        """Build a basic report when LLM is unavailable.

        Uses pre-computed scores and dimension summaries to construct
        a simple but informative report without LLM assistance.

        Args:
            stock_id: Taiwan stock ID.
            stock_name: Stock display name.
            analysis: AnalysisResult with all dimension data.

        Returns:
            Markdown-formatted fallback report.
        """
        signal_map = {
            "strong_buy": "強力買進",
            "buy": "買進",
            "neutral": "持有/觀望",
            "sell": "賣出",
            "strong_sell": "強力賣出",
        }
        signal_zh = signal_map.get(analysis.overall_signal, "觀望")

        lines = [
            f"# {stock_name}（{stock_id}）分析報告",
            "",
            f"**綜合評分:** {analysis.overall_score:.1f} 分",
            f"**建議:** {signal_zh}",
            f"**信心度:** {analysis.confidence:.0%}",
            f"**市場體制:** {analysis.regime}",
            "",
            "---",
            "",
        ]

        dimension_names = {
            "news": "一、消息面分析",
            "fundamental": "二、基本面分析",
            "technical": "三、技術面分析",
            "institutional": "四、籌碼面分析",
            "macro": "五、總體經濟面分析",
        }

        for dim_key, dim_title in dimension_names.items():
            detail = analysis.dimension_details.get(dim_key, {})
            score = analysis.scores.get(dim_key, 0)
            summary = detail.get("summary", "資料不足，無法進行分析。")

            lines.append(f"## {dim_title}")
            lines.append(f"**評分:** {score:.1f} 分")
            lines.append("")
            lines.append(summary)
            lines.append("")

        lines.extend([
            "## 六、綜合評估與建議",
            "",
            f"綜合五大維度分析，系統給予 {analysis.overall_score:.1f} 分的評分，"
            f"建議「{signal_zh}」。",
            "",
            "*注意: 此為系統自動生成的基礎報告（AI 服務暫時不可用），"
            "僅供參考，不構成投資建議。*",
        ])

        return "\n".join(lines)

    @staticmethod
    def _infer_risk_from_score(score: float) -> str:
        """Infer risk level from overall score magnitude."""
        abs_score = abs(score)
        if abs_score >= 50:
            return "LOW" if score > 0 else "HIGH"
        elif abs_score >= 20:
            return "MEDIUM"
        return "MEDIUM"


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

report_generator = ReportGenerator()
