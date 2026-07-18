"""Live market data with Finnhub → Yahoo Finance → demo fallback.

Paper trading still uses these quotes as simulated fill prices — no real brokerage.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import get_settings

# Offline / API-failure fallback (same tickers as the original demo desk)
BASE_DEMO_PRICES: dict[str, float] = {
    "NVDA": 128.50,
    "MSFT": 425.20,
    "AMD": 162.80,
    "GOOG": 178.40,
    "GOOGL": 178.40,
    "AAPL": 228.10,
    "TSLA": 248.60,
    "META": 585.30,
    "AMZN": 198.70,
    "PLTR": 72.40,
    "CRM": 312.50,
}

DEMO_COMPANY: dict[str, dict[str, Any]] = {
    "NVDA": {"name": "NVIDIA Corporation", "sector": "Technology", "marketCap": 3.1e12},
    "MSFT": {"name": "Microsoft Corporation", "sector": "Technology", "marketCap": 3.1e12},
    "AMD": {"name": "Advanced Micro Devices", "sector": "Technology", "marketCap": 2.6e11},
    "GOOG": {"name": "Alphabet Inc.", "sector": "Communication Services", "marketCap": 2.1e12},
    "GOOGL": {"name": "Alphabet Inc.", "sector": "Communication Services", "marketCap": 2.1e12},
    "AAPL": {"name": "Apple Inc.", "sector": "Technology", "marketCap": 3.4e12},
    "TSLA": {"name": "Tesla, Inc.", "sector": "Consumer Cyclical", "marketCap": 8.0e11},
    "META": {"name": "Meta Platforms, Inc.", "sector": "Communication Services", "marketCap": 1.5e12},
    "AMZN": {"name": "Amazon.com, Inc.", "sector": "Consumer Cyclical", "marketCap": 2.0e12},
    "PLTR": {"name": "Palantir Technologies", "sector": "Technology", "marketCap": 1.5e11},
    "CRM": {"name": "Salesforce, Inc.", "sector": "Technology", "marketCap": 2.9e11},
}

# Mutable copy used only when demo seed bumps marks for walkthrough P&L
_DEMO_PRICES: dict[str, float] = dict(BASE_DEMO_PRICES)

_CACHE: dict[str, tuple[float, "MarketQuote"]] = {}
_CACHE_TTL_SEC = 60.0


@dataclass
class MarketQuote:
    symbol: str
    price: float
    company_name: str
    market_cap: float | None = None
    sector: str | None = None
    change: float | None = None
    change_percent: float | None = None
    history: list[dict[str, Any]] = field(default_factory=list)
    source: str = "demo"
    as_of: str = ""

    def to_api(self) -> dict[str, Any]:
        """CamelCase payload for the frontend (additive field)."""
        return {
            "symbol": self.symbol,
            "price": round(self.price, 4),
            "companyName": self.company_name,
            "marketCap": self.market_cap,
            "sector": self.sector,
            "change": round(self.change, 4) if self.change is not None else None,
            "changePercent": round(self.change_percent, 4)
            if self.change_percent is not None
            else None,
            "history": self.history,
            "source": self.source,
            "asOf": self.as_of or datetime.now(timezone.utc).isoformat(),
        }


def get_demo_price(symbol: str) -> float:
    return _DEMO_PRICES.get(symbol.upper(), BASE_DEMO_PRICES.get(symbol.upper(), 100.0))


def bump_demo_prices(multipliers: dict[str, float]) -> None:
    """Reset demo marks, then apply multipliers (demo seed only)."""
    _DEMO_PRICES.clear()
    _DEMO_PRICES.update(BASE_DEMO_PRICES)
    for symbol, mult in multipliers.items():
        key = symbol.upper()
        if key in BASE_DEMO_PRICES:
            _DEMO_PRICES[key] = round(BASE_DEMO_PRICES[key] * mult, 2)


def _demo_quote(symbol: str) -> MarketQuote:
    symbol = symbol.upper()
    price = get_demo_price(symbol)
    meta = DEMO_COMPANY.get(symbol, {"name": symbol, "sector": "Unknown", "marketCap": None})
    # Synthetic recent history around the demo price
    history = []
    base = price * 0.96
    for i in range(14):
        day = datetime.now(timezone.utc).date().toordinal() - (13 - i)
        d = datetime.fromordinal(day).date().isoformat()
        close = round(base + (price - base) * (i / 13), 2)
        history.append({"date": d, "close": close})
    prev = history[-2]["close"] if len(history) > 1 else price
    change = round(price - prev, 2)
    change_pct = round((change / prev) * 100, 2) if prev else 0.0
    return MarketQuote(
        symbol=symbol,
        price=price,
        company_name=str(meta["name"]),
        market_cap=meta.get("marketCap"),
        sector=meta.get("sector"),
        change=change,
        change_percent=change_pct,
        history=history,
        source="demo",
        as_of=datetime.now(timezone.utc).isoformat(),
    )


def _yahoo_symbol(symbol: str) -> str:
    return symbol.upper()


async def _fetch_finnhub(symbol: str, token: str) -> MarketQuote | None:
    symbol = symbol.upper()
    # Finnhub uses GOOGL for Alphabet class A; try both for GOOG
    candidates = [symbol]
    if symbol == "GOOG":
        candidates = ["GOOGL", "GOOG"]

    async with httpx.AsyncClient(timeout=8.0) as client:
        for sym in candidates:
            quote_r = await client.get(
                "https://finnhub.io/api/v1/quote",
                params={"symbol": sym, "token": token},
            )
            if quote_r.status_code != 200:
                continue
            quote = quote_r.json()
            price = float(quote.get("c") or 0)
            if price <= 0:
                continue

            profile: dict[str, Any] = {}
            try:
                prof_r = await client.get(
                    "https://finnhub.io/api/v1/stock/profile2",
                    params={"symbol": sym, "token": token},
                )
                if prof_r.status_code == 200:
                    profile = prof_r.json() or {}
            except Exception:
                pass

            history: list[dict[str, Any]] = []
            try:
                now = int(time.time())
                from_ts = now - 30 * 24 * 3600
                candle_r = await client.get(
                    "https://finnhub.io/api/v1/stock/candle",
                    params={
                        "symbol": sym,
                        "resolution": "D",
                        "from": from_ts,
                        "to": now,
                        "token": token,
                    },
                )
                if candle_r.status_code == 200:
                    candle = candle_r.json() or {}
                    if candle.get("s") == "ok":
                        for ts, close in zip(candle.get("t", []), candle.get("c", [])):
                            history.append(
                                {
                                    "date": datetime.fromtimestamp(
                                        ts, tz=timezone.utc
                                    ).date().isoformat(),
                                    "close": round(float(close), 4),
                                }
                            )
            except Exception:
                pass

            prev_close = float(quote.get("pc") or 0) or None
            change = float(quote.get("d") or 0) if quote.get("d") is not None else None
            change_pct = (
                float(quote.get("dp") or 0) if quote.get("dp") is not None else None
            )
            if change is None and prev_close:
                change = price - prev_close
                change_pct = (change / prev_close) * 100 if prev_close else None

            market_cap = profile.get("marketCapitalization")
            if market_cap is not None:
                # Finnhub returns market cap in millions
                market_cap = float(market_cap) * 1_000_000

            return MarketQuote(
                symbol=symbol,
                price=price,
                company_name=profile.get("name") or DEMO_COMPANY.get(symbol, {}).get("name", symbol),
                market_cap=market_cap,
                sector=profile.get("finnhubIndustry") or profile.get("gics") or None,
                change=change,
                change_percent=change_pct,
                history=history[-30:],
                source="finnhub",
                as_of=datetime.now(timezone.utc).isoformat(),
            )
    return None


async def _fetch_yahoo(symbol: str) -> MarketQuote | None:
    symbol = _yahoo_symbol(symbol)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AlphaAI/1.0; research-paper-trading)",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=8.0, headers=headers, follow_redirects=True) as client:
        chart_r = await client.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"range": "1mo", "interval": "1d", "includePrePost": "false"},
        )
        if chart_r.status_code != 200:
            return None
        payload = chart_r.json()
        results = (payload.get("chart") or {}).get("result") or []
        if not results:
            return None
        result = results[0]
        meta = result.get("meta") or {}
        price = float(meta.get("regularMarketPrice") or meta.get("previousClose") or 0)
        if price <= 0:
            return None

        prev = float(meta.get("chartPreviousClose") or meta.get("previousClose") or 0)
        change = price - prev if prev else None
        change_pct = ((change / prev) * 100) if prev and change is not None else None

        timestamps = result.get("timestamp") or []
        quotes = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        closes = quotes.get("close") or []
        history: list[dict[str, Any]] = []
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            history.append(
                {
                    "date": datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat(),
                    "close": round(float(close), 4),
                }
            )

        company_name = meta.get("longName") or meta.get("shortName") or symbol
        market_cap = None
        sector = None

        # Best-effort company profile (may be rate-limited)
        try:
            sum_r = await client.get(
                f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}",
                params={"modules": "price,summaryProfile"},
            )
            if sum_r.status_code == 200:
                sm = sum_r.json()
                qr = ((sm.get("quoteSummary") or {}).get("result") or [None])[0] or {}
                price_mod = qr.get("price") or {}
                profile = qr.get("summaryProfile") or {}
                company_name = (
                    (price_mod.get("longName") or {}).get("raw")
                    or price_mod.get("longName")
                    or (price_mod.get("shortName") or {}).get("raw")
                    or company_name
                )
                if isinstance(company_name, dict):
                    company_name = company_name.get("raw") or symbol
                mc = price_mod.get("marketCap") or {}
                if isinstance(mc, dict):
                    market_cap = mc.get("raw")
                elif mc:
                    market_cap = float(mc)
                sector = profile.get("sector")
        except Exception:
            pass

        if not company_name or company_name == symbol:
            company_name = DEMO_COMPANY.get(symbol, {}).get("name", symbol)
        if sector is None:
            sector = DEMO_COMPANY.get(symbol, {}).get("sector")
        if market_cap is None:
            market_cap = DEMO_COMPANY.get(symbol, {}).get("marketCap")

        return MarketQuote(
            symbol=symbol,
            price=price,
            company_name=str(company_name),
            market_cap=float(market_cap) if market_cap is not None else None,
            sector=sector,
            change=change,
            change_percent=change_pct,
            history=history[-30:],
            source="yahoo",
            as_of=datetime.now(timezone.utc).isoformat(),
        )


async def get_quote(symbol: str, *, use_cache: bool = True) -> MarketQuote:
    """Current quote + profile + recent history. Never raises — falls back to demo."""
    symbol = symbol.upper().strip()
    if not symbol:
        return _demo_quote("UNKNOWN")

    now = time.time()
    if use_cache and symbol in _CACHE:
        ts, cached = _CACHE[symbol]
        if now - ts < _CACHE_TTL_SEC:
            return cached

    settings = get_settings()
    quote: MarketQuote | None = None

    if settings.finnhub_api_key:
        try:
            quote = await _fetch_finnhub(symbol, settings.finnhub_api_key)
        except Exception as e:
            print(f"Finnhub fetch failed for {symbol}: {e}")

    if quote is None:
        try:
            quote = await _fetch_yahoo(symbol)
        except Exception as e:
            print(f"Yahoo fetch failed for {symbol}: {e}")

    if quote is None:
        quote = _demo_quote(symbol)

    _CACHE[symbol] = (now, quote)
    return quote


async def get_price(symbol: str) -> float:
    quote = await get_quote(symbol)
    return quote.price


async def get_prices(symbols: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for sym in symbols:
        out[sym.upper()] = await get_price(sym)
    return out
