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


def _normalize_tickers(raw: Any, fallback: list[str]) -> list[str]:
    if not isinstance(raw, list) or not raw:
        return fallback
    out: list[str] = []
    for item in raw:
        ticker = str(item).strip().upper().replace(".", "-")
        if ticker and ticker not in out and 1 <= len(ticker) <= 6:
            out.append(ticker)
    return out[:8] if out else fallback


# Theme playbooks for offline / no-Gemini strategy generation
STRATEGY_THEMES: list[dict[str, Any]] = [
    {
        "id": "renewable",
        "keywords": [
            "renewable",
            "clean energy",
            "solar",
            "wind",
            "green energy",
            "climate",
            "esg energy",
        ],
        "name": "Renewable Power Builders",
        "stocks": ["ENPH", "FSLR", "NEE", "SEDG", "BE"],
        "buy": [
            "Policy or subsidy tailwinds supporting clean-power deployment",
            "Improving project backlog or installation growth",
            "Relative strength vs broader utilities / energy peers",
        ],
        "sell": [
            "Rate-sensitive multiple expansion without earnings support",
            "Negative policy or permitting headlines",
            "Break of multi-week support after volume spike",
        ],
        "summary": "Theme sleeve focused on solar, utilities, and clean-power enablers.",
    },
    {
        "id": "cybersecurity",
        "keywords": [
            "cyber",
            "security",
            "infosec",
            "firewall",
            "zero trust",
            "ransomware",
        ],
        "name": "Cybersecurity Moat",
        "stocks": ["CRWD", "PANW", "ZS", "S", "FTNT"],
        "buy": [
            "Rising threat environment driving budget priority",
            "Strong net retention / platform attach rates",
            "Breakout above consolidation with healthy volume",
        ],
        "sell": [
            "Guidance cut or elongated sales cycles",
            "Multiple compression after growth deceleration",
            "Breach-related reputational shock without clear remediation",
        ],
        "summary": "Defensive-growth sleeve of endpoint, network, and cloud security leaders.",
    },
    {
        "id": "healthcare",
        "keywords": [
            "health",
            "healthcare",
            "biotech",
            "pharma",
            "medical",
            "hospital",
            "drug",
        ],
        "name": "Healthcare Innovators",
        "stocks": ["UNH", "LLY", "ISRG", "JNJ", "ABBV"],
        "buy": [
            "Pipeline or product catalysts with clear commercial path",
            "Stable cash flow and defensive demand profile",
            "Relative outperformance vs healthcare sector ETF",
        ],
        "sell": [
            "Adverse regulatory, pricing, or trial outcome news",
            "Valuation stretch without earnings confirmation",
            "Deteriorating volume leadership vs sector peers",
        ],
        "summary": "Mix of managed care, therapeutics, and med-tech for healthcare exposure.",
    },
    {
        "id": "robotics",
        "keywords": [
            "robot",
            "robotics",
            "automation",
            "industrial ai",
            "factory",
            "cobot",
        ],
        "name": "Robotics & Automation",
        "stocks": ["ISRG", "ROK", "TER", "PATH", "IRBT"],
        "buy": [
            "Capex cycle turning up for factory / hospital automation",
            "Order growth or utilization metrics improving",
            "Momentum confirming a break from base with sector leadership",
        ],
        "sell": [
            "Industrial slowdown or cancelled automation programs",
            "Margin pressure from input costs or competition",
            "Failed breakout and return below key moving averages",
        ],
        "summary": "Automation and robotics names spanning surgical, industrial, and software layers.",
    },
    {
        "id": "fintech",
        "keywords": [
            "fintech",
            "payments",
            "digital bank",
            "neobank",
            "payments",
            "crypto exchange",
            "bnpl",
        ],
        "name": "Fintech Rails",
        "stocks": ["SQ", "PYPL", "COIN", "SOFI", "AFRM"],
        "buy": [
            "Payment volume or user growth re-accelerating",
            "Credit / funding costs stabilizing",
            "Relative strength vs financials after a constructive base",
        ],
        "sell": [
            "Rising charge-offs or funding stress",
            "Regulatory actions hitting take-rates or product mix",
            "Break of rising channel with expanding volatility",
        ],
        "summary": "Digital payments, consumer finance, and crypto-adjacent fintech exposure.",
    },
    {
        "id": "ai",
        "keywords": [
            "ai",
            "artificial intelligence",
            "llm",
            "gpu",
            "machine learning",
            "semiconductor",
            "chip",
        ],
        "name": "AI Infrastructure Momentum",
        "stocks": ["NVDA", "MSFT", "AMD", "AVGO", "PLTR"],
        "buy": [
            "Evidence of AI capex or inference demand continuing",
            "Earnings growth confirming the AI narrative",
            "Price momentum with sector leadership",
        ],
        "sell": [
            "Capex digestion or inventory digestion signals",
            "Competitive share-shift headlines without offsetting growth",
            "Volatility spike without fundamental confirmation",
        ],
        "summary": "AI compute, cloud platforms, and application-layer beneficiaries.",
    },
    {
        "id": "ev",
        "keywords": ["ev", "electric vehicle", "autonomous", "auto tech", "battery"],
        "name": "EV & Mobility Tech",
        "stocks": ["TSLA", "RIVN", "LCID", "QS", "ALB"],
        "buy": [
            "Delivery or adoption metrics beating expectations",
            "Battery cost curve or range improvements",
            "Constructive price action after a high-volume base",
        ],
        "sell": [
            "Demand miss, price war, or margin shock",
            "Commodity cost spikes crushing unit economics",
            "Breakdown below multi-month support",
        ],
        "summary": "Electric vehicles and battery-materials exposure for mobility tech.",
    },
    {
        "id": "dividend",
        "keywords": ["dividend", "income", "yield", "value", "defensive"],
        "name": "Quality Income Core",
        "stocks": ["JNJ", "PG", "KO", "PEP", "VZ"],
        "buy": [
            "Stable free-cash-flow coverage of the dividend",
            "Reasonable valuation vs history and peers",
            "Defensive bid during risk-off tapes",
        ],
        "sell": [
            "Dividend cut risk or payout ratio stress",
            "Secular demand erosion in the category",
            "Yield compression after sharp re-rating",
        ],
        "summary": "Lower-volatility quality names oriented to income and capital preservation.",
    },
    {
        "id": "cloud",
        "keywords": ["cloud", "saas", "software", "enterprise software"],
        "name": "Cloud Software Compounders",
        "stocks": ["MSFT", "AMZN", "CRM", "NOW", "SNOW"],
        "buy": [
            "Cloud consumption or remaining performance obligation growth",
            "Expanding operating margins with durable retention",
            "Relative strength vs software peers",
        ],
        "sell": [
            "Optimization cycle lengthening without offsetting AI attach",
            "Customer concentration or competitive displacement risk",
            "Failed earnings reaction and loss of momentum",
        ],
        "summary": "Hyperscale and enterprise SaaS compounders for cloud exposure.",
    },
]


def _infer_risk(description: str) -> str:
    d = description.lower()
    if any(w in d for w in ("low", "conservative", "defensive", "income", "dividend")):
        return "Low"
    if any(w in d for w in ("high", "aggressive", "speculative", "moonshot")):
        return "High"
    return "Medium"


def _match_theme(description: str) -> dict[str, Any]:
    """Score theme keywords against the user brief; fall back to a blended growth sleeve."""
    d = description.lower()
    best: dict[str, Any] | None = None
    best_score = 0
    for theme in STRATEGY_THEMES:
        score = 0
        for kw in theme["keywords"]:
            if kw in d:
                # Longer phrases count more
                score += 2 if " " in kw else 1
        if score > best_score:
            best_score = score
            best = theme

    if best and best_score > 0:
        return best

    # Multi-theme blend from explicit mentions of several verticals
    matched = [t for t in STRATEGY_THEMES if any(kw in d for kw in t["keywords"])]
    if len(matched) >= 2:
        stocks: list[str] = []
        for t in matched[:3]:
            for s in t["stocks"][:2]:
                if s not in stocks:
                    stocks.append(s)
        return {
            "id": "multi",
            "name": "Multi-Theme Growth Sleeve",
            "stocks": stocks[:6],
            "buy": [
                "Confirm theme catalysts across selected verticals",
                "Prefer leaders with relative strength in each theme",
                "Scale in on constructive pullbacks within the uptrend",
            ],
            "sell": [
                "Theme narrative breaks (policy, demand, or funding shock)",
                "Correlation spike and indiscriminate risk-off selling",
                "Individual name loses leadership vs its theme peers",
            ],
            "summary": "Diversified sleeve mixing the themes detected in the brief.",
        }

    return {
        "id": "balanced",
        "name": "Balanced Growth Basket",
        "stocks": ["AAPL", "MSFT", "AMZN", "GOOG", "BRK-B"],
        "buy": [
            "Broad market trend remains constructive",
            "Company-level earnings and guidance stay resilient",
            "Pullbacks hold above rising medium-term averages",
        ],
        "sell": [
            "Market regime shifts to sustained risk-off",
            "Fundamental deterioration in a core holding",
            "Position sizing breaches risk limits after volatility expansion",
        ],
        "summary": "Diversified mega-cap growth sleeve when no single theme dominates the brief.",
    }


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
        fallback = self._mock_strategy(description)
        if not self.available:
            return fallback

        theme_hints = ", ".join(
            t["id"] for t in STRATEGY_THEMES if t["id"] not in {"ai", "ev", "dividend", "cloud"}
        )
        prompt = f"""You are AlphaAI, an AI hedge fund research assistant for educational paper trading only.

User brief:
"{description}"

Generate a DISTINCT strategy matched to the brief. Do NOT default to NVDA/MSFT/AMD/GOOG unless the brief is explicitly about AI/semiconductors.

Supported theme examples (pick what fits; invent a coherent sleeve if needed):
renewable energy, cybersecurity, healthcare, robotics, fintech, {theme_hints}, cloud, EV, dividends/value, or a multi-theme blend.

Requirements:
- stocks: 4–6 real, liquid US-listed tickers that fit the theme (use official symbols)
- buy/sell rules must be theme-specific, not generic boilerplate
- riskLevel must reflect the brief and theme volatility
- Never claim certainty. Frame as AI-assisted paper-trading research.

Respond ONLY with valid JSON (no markdown):
{{
  "name": "short strategy name",
  "riskLevel": "Low" | "Medium" | "High",
  "stocks": ["TICKER1", "TICKER2", "TICKER3", "TICKER4"],
  "rules": {{
    "buy": ["theme-specific buy rule 1", "rule 2", "rule 3"],
    "sell": ["theme-specific sell rule 1", "rule 2", "rule 3"]
  }},
  "summary": "1-2 sentence summary of the strategy thesis"
}}"""

        try:
            text = await self._generate(prompt)
            data = self._extract_json(text)
            rules = data.get("rules") if isinstance(data.get("rules"), dict) else {}
            risk = str(data.get("riskLevel") or fallback["riskLevel"]).title()
            if risk not in {"Low", "Medium", "High"}:
                risk = fallback["riskLevel"]
            return {
                "name": str(data.get("name") or fallback["name"]).strip() or fallback["name"],
                "riskLevel": risk,
                "stocks": _normalize_tickers(data.get("stocks"), fallback["stocks"]),
                "rules": {
                    "buy": _as_str_list(rules.get("buy")) or fallback["rules"]["buy"],
                    "sell": _as_str_list(rules.get("sell")) or fallback["rules"]["sell"],
                },
                "summary": str(data.get("summary") or description).strip() or description,
            }
        except Exception as e:
            print(f"Gemini strategy error: {e}")
            return fallback

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
        theme = _match_theme(description)
        risk = _infer_risk(description)
        # Theme defaults: income → Low, speculative themes → High unless overridden
        if risk == "Medium":
            if theme.get("id") in {"dividend"}:
                risk = "Low"
            elif theme.get("id") in {"fintech", "ev", "robotics", "ai"}:
                risk = "High" if any(
                    w in description.lower() for w in ("high", "aggressive", "speculative")
                ) else "Medium"

        name = theme["name"]
        # Reflect risk wording in the name when the user asked for it explicitly
        d = description.lower()
        if "low" in d and "Low" not in name:
            name = f"Conservative {name}"
        elif "high" in d or "aggressive" in d:
            name = f"Aggressive {name}"

        summary = theme.get("summary") or description
        if description.strip():
            summary = f"{summary} Brief: {description.strip()}"

        return {
            "name": name,
            "riskLevel": risk,
            "stocks": list(theme["stocks"])[:6],
            "rules": {
                "buy": list(theme["buy"]),
                "sell": list(theme["sell"]),
            },
            "summary": summary,
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
