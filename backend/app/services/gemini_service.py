from __future__ import annotations

import json
import re
from typing import Any

from app.config import get_settings
from app.models.schemas import (
    StrategyRules,
    StockAnalysis,
    PredictionResult,
)

# Seed price table for paper trading (demo) — mutable for mark-to-market
BASE_DEMO_PRICES: dict[str, float] = {
    "NVDA": 128.50,
    "MSFT": 425.20,
    "AMD": 162.80,
    "GOOG": 178.40,
    "AAPL": 228.10,
    "TSLA": 248.60,
    "META": 585.30,
    "AMZN": 198.70,
    "PLTR": 72.40,
    "CRM": 312.50,
}

DEMO_PRICES: dict[str, float] = dict(BASE_DEMO_PRICES)


def get_demo_price(symbol: str) -> float:
    return DEMO_PRICES.get(symbol.upper(), 100.0)


def bump_demo_prices(multipliers: dict[str, float]) -> None:
    """Reset to base prices, then apply mark-to-market multipliers for demo P&L."""
    DEMO_PRICES.clear()
    DEMO_PRICES.update(BASE_DEMO_PRICES)
    for symbol, mult in multipliers.items():
        key = symbol.upper()
        if key in DEMO_PRICES:
            DEMO_PRICES[key] = round(BASE_DEMO_PRICES[key] * mult, 2)


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

    async def analyze_stock(self, symbol: str) -> StockAnalysis:
        symbol = symbol.upper().strip()
        if not self.available:
            return self._mock_analysis(symbol)

        prompt = f"""You are AlphaAI, an AI-assisted stock research tool for educational paper trading.
Analyze {symbol}. Never claim certainty. Use wording like "potential opportunity" and "risk assessment".

Respond ONLY with valid JSON:
{{
  "stock": "Company Name",
  "recommendation": "BUY" | "HOLD" | "SELL",
  "confidence": 0-100,
  "positives": ["...", "...", "..."],
  "risks": ["...", "...", "..."],
  "summary": "brief AI-assisted analysis summary"
}}"""

        try:
            text = await self._generate(prompt)
            data = self._extract_json(text)
            return StockAnalysis(
                stock=data.get("stock", symbol),
                symbol=symbol,
                recommendation=data.get("recommendation", "HOLD"),
                confidence=int(data.get("confidence", 50)),
                positives=data.get("positives", []),
                risks=data.get("risks", []),
                summary=data.get("summary", "AI-assisted analysis unavailable."),
            )
        except Exception as e:
            print(f"Gemini analysis error: {e}")
            return self._mock_analysis(symbol)

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

Never claim certainty. This is AI-assisted analysis only."""

        try:
            text = await self._generate(prompt)
            data = self._extract_json(text)
            return PredictionResult(
                market=market,
                question=question,
                prediction=data.get("prediction", "YES"),
                confidence=int(data.get("confidence", 55)),
                reasoning=data.get("reasoning", []),
                risks=data.get("risks", []),
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

    def _mock_analysis(self, symbol: str) -> StockAnalysis:
        catalog: dict[str, dict] = {
            "NVDA": {
                "stock": "NVIDIA",
                "recommendation": "BUY",
                "confidence": 82,
                "positives": [
                    "AI chip demand remains a structural growth driver",
                    "Revenue growth trend supports expansion thesis",
                    "Market momentum aligns with sector leadership",
                ],
                "risks": [
                    "High valuation relative to historical averages",
                    "Intensifying competition in AI accelerators",
                    "Cyclical semiconductor demand risk",
                ],
                "summary": "AI-assisted analysis suggests a potential opportunity in NVDA based on AI infrastructure demand, balanced against valuation and competition risks.",
            },
            "MSFT": {
                "stock": "Microsoft",
                "recommendation": "BUY",
                "confidence": 78,
                "positives": [
                    "Cloud and Copilot monetization runway",
                    "Diversified enterprise revenue base",
                    "Strong balance sheet and cash generation",
                ],
                "risks": [
                    "Regulatory scrutiny in cloud markets",
                    "AI spend ROI uncertainty for customers",
                    "Valuation premium to broader market",
                ],
                "summary": "AI-assisted analysis frames MSFT as a potential opportunity via cloud/AI leverage, with regulatory and valuation risk assessment.",
            },
            "AMD": {
                "stock": "Advanced Micro Devices",
                "recommendation": "HOLD",
                "confidence": 64,
                "positives": [
                    "Data center GPU share gains potential",
                    "CPU competitive positioning improving",
                    "AI accelerator roadmap momentum",
                ],
                "risks": [
                    "Execution risk vs larger competitors",
                    "Margin pressure in competitive segments",
                    "Near-term demand visibility mixed",
                ],
                "summary": "AI-assisted analysis indicates a mixed risk assessment for AMD — constructive long-term thesis with near-term uncertainty.",
            },
            "GOOG": {
                "stock": "Alphabet",
                "recommendation": "BUY",
                "confidence": 74,
                "positives": [
                    "Search monetization resilience",
                    "Cloud growth acceleration potential",
                    "Deep AI research and product integration",
                ],
                "risks": [
                    "Antitrust and regulatory overhang",
                    "AI search disruption scenarios",
                    "Ad cycle sensitivity",
                ],
                "summary": "AI-assisted analysis sees a potential opportunity in GOOG from AI + cloud, tempered by regulatory risk assessment.",
            },
        }
        data = catalog.get(
            symbol,
            {
                "stock": symbol,
                "recommendation": "HOLD",
                "confidence": 55,
                "positives": [
                    "Sector exposure aligned with growth themes",
                    "Liquidity supports paper-trading simulation",
                    "Watchlist candidate for further research",
                ],
                "risks": [
                    "Limited company-specific data in demo mode",
                    "Market volatility can reverse thesis quickly",
                    "Macro and sector rotation risks",
                ],
                "summary": f"AI-assisted analysis for {symbol}: preliminary risk assessment only — not a certainty signal.",
            },
        )
        return StockAnalysis(symbol=symbol, **data)

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
                "Confidence is probabilistic, never certain",
            ],
        )


gemini_service = GeminiService()
