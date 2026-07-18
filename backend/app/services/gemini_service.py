from __future__ import annotations

import json
import re
from typing import Any

from app.config import get_settings
from app.models.schemas import (
    StockAnalysis,
    PredictionResult,
)


def _format_cap(value: Any) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "unavailable"
    if n >= 1e12:
        return f"${n / 1e12:.2f}T"
    if n >= 1e9:
        return f"${n / 1e9:.2f}B"
    if n >= 1e6:
        return f"${n / 1e6:.1f}M"
    return f"${n:,.0f}"


def _history_stats(history: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Derive recent movement metrics from close history."""
    closes: list[float] = []
    for point in history or []:
        try:
            closes.append(float(point["close"]))
        except (KeyError, TypeError, ValueError):
            continue
    if len(closes) < 2:
        return {}

    latest = closes[-1]
    first = closes[0]
    week_ago = closes[-6] if len(closes) >= 6 else closes[0]
    high = max(closes)
    low = min(closes)
    period_return = ((latest - first) / first) * 100 if first else 0.0
    week_return = ((latest - week_ago) / week_ago) * 100 if week_ago else 0.0
    # Simple volatility proxy: avg absolute day-to-day % move
    day_moves = [
        abs((closes[i] - closes[i - 1]) / closes[i - 1]) * 100
        for i in range(1, len(closes))
        if closes[i - 1]
    ]
    avg_abs_move = sum(day_moves) / len(day_moves) if day_moves else 0.0

    return {
        "historyPoints": len(closes),
        "periodStartClose": round(first, 4),
        "periodEndClose": round(latest, 4),
        "periodReturnPct": round(period_return, 2),
        "approxWeekReturnPct": round(week_return, 2),
        "periodHigh": round(high, 4),
        "periodLow": round(low, 4),
        "avgAbsDailyMovePct": round(avg_abs_move, 2),
        "nearHigh": latest >= high * 0.98,
        "nearLow": latest <= low * 1.02,
    }


def build_market_brief(symbol: str, market: dict[str, Any] | None) -> str:
    """Structured market brief for Gemini — never invent prices."""
    m = market or {}
    stats = _history_stats(m.get("history") if isinstance(m.get("history"), list) else [])
    company = m.get("companyName") or symbol
    price = m.get("price")
    change = m.get("change")
    change_pct = m.get("changePercent")
    sector = m.get("sector") or "unavailable"
    market_cap = _format_cap(m.get("marketCap"))
    source = m.get("source") or "unknown"
    as_of = m.get("asOf") or "unavailable"

    lines = [
        "=== MARKET DATA (authoritative — do not invent or override prices) ===",
        f"Company name: {company}",
        f"Ticker: {symbol.upper()}",
        f"Current price: {price if price is not None else 'unavailable'}",
        f"Daily change: {change if change is not None else 'unavailable'} "
        f"({change_pct if change_pct is not None else 'unavailable'}%)",
        f"Sector: {sector}",
        f"Market cap: {market_cap}",
        f"Data source: {source}",
        f"As of: {as_of}",
    ]

    if stats:
        lines.extend(
            [
                "--- Recent price movement ---",
                f"History window: {stats['historyPoints']} daily closes",
                f"Period return: {stats['periodReturnPct']}%",
                f"Approx. 1-week return: {stats['approxWeekReturnPct']}%",
                f"Period high / low: {stats['periodHigh']} / {stats['periodLow']}",
                f"Avg abs daily move: {stats['avgAbsDailyMovePct']}%",
                f"Trading near period high: {stats['nearHigh']}",
                f"Trading near period low: {stats['nearLow']}",
            ]
        )
    else:
        lines.append("Recent price movement: limited history available")

    lines.append("=== END MARKET DATA ===")
    return "\n".join(lines)


def _clamp_confidence(value: Any, default: int = 55) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, min(100, n))


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


class GeminiService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._model = None
        if self.settings.gemini_api_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=self.settings.gemini_api_key)
                self._model = genai.GenerativeModel("gemini-1.5-flash")
            except Exception as e:
                print(f"Gemini init failed: {e}")

    @property
    def available(self) -> bool:
        return self._model is not None

    async def _generate(self, prompt: str) -> str:
        if not self._model:
            raise RuntimeError("Gemini not configured")
        response = self._model.generate_content(prompt)
        return response.text or ""

    def _extract_json(self, text: str) -> dict[str, Any]:
        text = text.strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fence:
            text = fence.group(1).strip()
        return json.loads(text)

    async def generate_strategy(self, description: str) -> dict[str, Any]:
        if not self.available:
            return self._mock_strategy(description)

        prompt = f"""You are AlphaAI, an AI hedge fund research assistant for paper trading only.
Generate a trading strategy from this user request:

"{description}"

Respond ONLY with valid JSON (no markdown):
{{
  "name": "short strategy name",
  "riskLevel": "Low" | "Medium" | "High",
  "stocks": ["TICKER1", "TICKER2", ...],
  "rules": {{
    "buy": ["rule1", "rule2", "rule3"],
    "sell": ["rule1", "rule2", "rule3"]
  }},
  "summary": "1-2 sentence description"
}}

Use real stock tickers. Never claim certainty. Frame as AI-assisted analysis."""

        try:
            text = await self._generate(prompt)
            data = self._extract_json(text)
            return {
                "name": data.get("name", "Custom Strategy"),
                "riskLevel": data.get("riskLevel", "Medium"),
                "stocks": data.get("stocks", ["NVDA", "MSFT"]),
                "rules": data.get("rules", {"buy": [], "sell": []}),
                "summary": data.get("summary", description),
            }
        except Exception as e:
            print(f"Gemini strategy error: {e}")
            return self._mock_strategy(description)

    async def analyze_stock(
        self, symbol: str, market_context: dict[str, Any] | None = None
    ) -> StockAnalysis:
        symbol = symbol.upper().strip()
        market = market_context or {}
        company = str(market.get("companyName") or symbol)
        brief = build_market_brief(symbol, market)

        if not self.available:
            return self._mock_analysis(symbol, market)

        prompt = f"""You are AlphaAI, an AI-assisted equity research desk for educational paper trading only.

Ground your entire analysis in the market data below. Do NOT invent prices, market caps, or percentage moves.
If a metric is unavailable, say so and lower confidence accordingly.
Use cautious wording: "AI-assisted analysis", "potential opportunity", "risk assessment".
Never claim certainty that the stock will rise or fall.

{brief}

Task: Produce an investment research note for {company} ({symbol}).

Respond ONLY with valid JSON (no markdown):
{{
  "stock": "{company}",
  "recommendation": "BUY" | "HOLD" | "SELL",
  "confidence": 0-100,
  "reasoning": [
    "step-by-step reason grounded in the provided data",
    "another reason tied to price movement / sector / metrics"
  ],
  "positives": ["supporting factor 1", "supporting factor 2", "supporting factor 3"],
  "risks": ["risk 1", "risk 2", "risk 3"],
  "summary": "2-3 sentence AI-assisted summary referencing the provided market data"
}}

CRITICAL — confidence meaning:
- confidence is how confident you are in the QUALITY of your reasoning given the available information.
- It is NOT the probability that the stock price will increase.
- Higher when data is complete and signals are consistent; lower when history is thin, metrics are missing, or signals conflict.
"""

        try:
            text = await self._generate(prompt)
            data = self._extract_json(text)
            rec = str(data.get("recommendation", "HOLD")).upper()
            if rec not in {"BUY", "HOLD", "SELL"}:
                rec = "HOLD"
            return StockAnalysis(
                stock=data.get("stock") or company,
                symbol=symbol,
                recommendation=rec,  # type: ignore[arg-type]
                confidence=_clamp_confidence(data.get("confidence"), 55),
                reasoning=_as_str_list(data.get("reasoning")),
                positives=_as_str_list(data.get("positives")),
                risks=_as_str_list(data.get("risks")),
                summary=str(
                    data.get("summary")
                    or "AI-assisted analysis based on available market data."
                ),
            )
        except Exception as e:
            print(f"Gemini analysis error: {e}")
            return self._mock_analysis(symbol, market)

    async def predict_market(
        self, market: str, question: str, context: str = ""
    ) -> PredictionResult:
        if not self.available:
            return self._mock_prediction(market, question)

        prompt = f"""You are AlphaAI Predict the 6ix bot — adapt stock-strategy logic to prediction markets.
Market: {market}
Question: {question}
Context: {context or "none"}

Respond ONLY with valid JSON:
{{
  "prediction": "YES" | "NO",
  "confidence": 0-100,
  "reasoning": ["...", "...", "..."],
  "risks": ["...", "..."]
}}

confidence = confidence in your reasoning given available information, NOT probability of YES.
Never claim certainty. This is AI-assisted analysis only."""

        try:
            text = await self._generate(prompt)
            data = self._extract_json(text)
            return PredictionResult(
                market=market,
                question=question,
                prediction=data.get("prediction", "YES"),
                confidence=_clamp_confidence(data.get("confidence"), 55),
                reasoning=_as_str_list(data.get("reasoning")),
                risks=_as_str_list(data.get("risks")),
            )
        except Exception as e:
            print(f"Gemini prediction error: {e}")
            return self._mock_prediction(market, question)

    def _mock_strategy(self, description: str) -> dict[str, Any]:
        desc_lower = description.lower()
        if "ai" in desc_lower or "tech" in desc_lower:
            stocks = ["NVDA", "MSFT", "AMD", "GOOG"]
            name = "AI Growth Momentum"
        elif "value" in desc_lower or "dividend" in desc_lower:
            stocks = ["AAPL", "MSFT", "AMZN"]
            name = "Quality Value Core"
        elif "ev" in desc_lower or "auto" in desc_lower:
            stocks = ["TSLA", "AMD", "NVDA"]
            name = "EV & Mobility Thesis"
        else:
            stocks = ["NVDA", "AAPL", "MSFT", "META"]
            name = "Balanced Growth Basket"

        risk = "Medium"
        if "low" in desc_lower:
            risk = "Low"
        elif "high" in desc_lower or "aggressive" in desc_lower:
            risk = "High"

        return {
            "name": name,
            "riskLevel": risk,
            "stocks": stocks,
            "rules": {
                "buy": [
                    "Strong earnings growth trajectory",
                    "Positive market sentiment signals",
                    "Increasing price momentum",
                ],
                "sell": [
                    "Elevated volatility without fundamentals",
                    "Negative news flow impact",
                    "Weakening fundamental indicators",
                ],
            },
            "summary": description,
        }

    def _mock_analysis(
        self, symbol: str, market: dict[str, Any] | None = None
    ) -> StockAnalysis:
        """Offline / no-Gemini path — still grounds output in provided market data."""
        m = market or {}
        company = str(m.get("companyName") or symbol)
        price = m.get("price")
        change_pct = m.get("changePercent")
        sector = m.get("sector")
        stats = _history_stats(m.get("history") if isinstance(m.get("history"), list) else [])
        source = m.get("source") or "demo"

        # Confidence in reasoning quality from data completeness (not upside odds)
        confidence = 48
        if price is not None:
            confidence += 12
        if change_pct is not None:
            confidence += 8
        if sector:
            confidence += 6
        if m.get("marketCap") is not None:
            confidence += 6
        if stats.get("historyPoints", 0) >= 10:
            confidence += 10
        elif stats.get("historyPoints", 0) >= 5:
            confidence += 5
        if source != "demo":
            confidence += 5
        # Cap: quote+history alone never justifies near-certainty without fundamentals
        confidence = _clamp_confidence(min(confidence, 82))

        period_ret = stats.get("periodReturnPct")
        week_ret = stats.get("approxWeekReturnPct")

        # Soft recommendation from available movement — clearly labeled as data-driven heuristic
        recommendation = "HOLD"
        if isinstance(change_pct, (int, float)) and isinstance(period_ret, (int, float)):
            if change_pct > 1.5 and period_ret > 3:
                recommendation = "BUY"
            elif change_pct < -2 and period_ret < -5:
                recommendation = "SELL"

        price_s = f"${float(price):.2f}" if isinstance(price, (int, float)) else "unavailable"
        chg_s = (
            f"{float(change_pct):+.2f}%"
            if isinstance(change_pct, (int, float))
            else "unavailable"
        )
        period_s = f"{period_ret:+.2f}%" if isinstance(period_ret, (int, float)) else "n/a"
        week_s = f"{week_ret:+.2f}%" if isinstance(week_ret, (int, float)) else "n/a"

        reasoning = [
            f"Grounded in {source} market data for {symbol}: last mark {price_s}, daily move {chg_s}.",
            f"Recent window return {period_s}; approx. 1-week return {week_s}.",
            (
                f"Sector context: {sector}."
                if sector
                else "Sector metadata unavailable — reasoning confidence reduced."
            ),
        ]

        positives = [
            f"Quoted company identity available: {company}",
            f"Daily change observed at {chg_s} against last close context",
        ]
        if isinstance(period_ret, (int, float)) and period_ret > 0:
            positives.append(f"Positive period return of {period_s} in the available history window")
        if m.get("marketCap") is not None:
            positives.append(f"Market cap reported at {_format_cap(m.get('marketCap'))}")

        risks = [
            "Paper-trading heuristic only — not a forecast of future returns",
            "Limited fundamental/news inputs beyond quote and recent closes",
        ]
        if source == "demo":
            risks.append("Using fallback demo marks — live API unavailable")
        if stats.get("avgAbsDailyMovePct", 0) > 2.5:
            risks.append(
                f"Elevated recent swing size (~{stats['avgAbsDailyMovePct']}% avg abs daily move)"
            )
        if not sector:
            risks.append("Missing sector classification weakens comparative assessment")

        summary = (
            f"AI-assisted analysis for {company} ({symbol}) at {price_s} "
            f"(daily {chg_s}, period {period_s}). "
            f"Recommendation {recommendation} reflects a risk assessment of the provided quote data. "
            f"Confidence {confidence}% measures strength of this reasoning given available information — "
            f"not the chance the stock rises."
        )

        return StockAnalysis(
            stock=company,
            symbol=symbol,
            recommendation=recommendation,  # type: ignore[arg-type]
            confidence=confidence,
            reasoning=reasoning,
            positives=positives[:4],
            risks=risks[:4],
            summary=summary,
        )

    def _mock_prediction(self, market: str, question: str) -> PredictionResult:
        q = question.lower()
        yes_lean = any(
            w in q for w in ["will", "above", "win", "pass", "increase", "grow"]
        )
        return PredictionResult(
            market=market,
            question=question,
            prediction="YES" if yes_lean else "NO",
            confidence=61 if yes_lean else 57,
            reasoning=[
                "Historical base rates lean modestly in this direction",
                "Narrative catalysts currently favor the predicted side",
                "Liquidity and attention metrics support the thesis",
            ],
            risks=[
                "Prediction markets can gap on sudden news",
                "Sample of public signals may be biased",
                "Confidence is in reasoning quality, never outcome certainty",
            ],
        )


gemini_service = GeminiService()
