"""Portfolio and trade persistence — MongoDB with in-memory fallback."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings
from app.database.connection import get_db, get_memory_store, using_memory
from app.models.schemas import Holding, Portfolio, Trade
from app.services.gemini_service import get_demo_price


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _oid() -> str:
    return str(uuid.uuid4())


async def ensure_user(user_id: str, name: str = "Trader") -> dict[str, Any]:
    settings = get_settings()
    if using_memory():
        store = get_memory_store()
        if user_id not in store["users"]:
            store["users"][user_id] = {
                "userId": user_id,
                "name": name,
                "createdAt": _now().isoformat(),
            }
            store["portfolios"][user_id] = {
                "userId": user_id,
                "cash": settings.starting_cash,
                "holdings": [],
                "startingBalance": settings.starting_cash,
                "history": [
                    {
                        "date": _now().date().isoformat(),
                        "value": settings.starting_cash,
                    }
                ],
            }
        return store["users"][user_id]

    db = get_db()
    assert db is not None
    existing = await db.users.find_one({"userId": user_id})
    if existing:
        return existing
    doc = {"userId": user_id, "name": name, "createdAt": _now()}
    await db.users.insert_one(doc)
    await db.portfolios.insert_one(
        {
            "userId": user_id,
            "cash": settings.starting_cash,
            "holdings": [],
            "startingBalance": settings.starting_cash,
            "history": [{"date": _now().date().isoformat(), "value": settings.starting_cash}],
        }
    )
    return doc


async def save_strategy(doc: dict[str, Any]) -> dict[str, Any]:
    doc = {**doc, "id": doc.get("id") or _oid()}
    if using_memory():
        store = get_memory_store()
        store["strategies"][doc["id"]] = doc
        return doc
    db = get_db()
    assert db is not None
    await db.strategies.insert_one({**doc, "_id": doc["id"]})
    return doc


async def list_strategies(user_id: str) -> list[dict[str, Any]]:
    if using_memory():
        store = get_memory_store()
        return [s for s in store["strategies"].values() if s.get("userId") == user_id]
    db = get_db()
    assert db is not None
    cursor = db.strategies.find({"userId": user_id}).sort("createdAt", -1)
    return await cursor.to_list(100)


async def get_strategy(strategy_id: str) -> dict[str, Any] | None:
    if using_memory():
        return get_memory_store()["strategies"].get(strategy_id)
    db = get_db()
    assert db is not None
    return await db.strategies.find_one({"$or": [{"id": strategy_id}, {"_id": strategy_id}]})


async def execute_trade(
    user_id: str,
    stock: str,
    trade_type: str,
    amount: float,
    confidence: int = 0,
    reasoning: str = "",
    strategy_id: str | None = None,
    price: float | None = None,
) -> dict[str, Any]:
    stock = stock.upper()
    px = price or get_demo_price(stock)
    if px <= 0:
        raise ValueError("Invalid price")
    if amount <= 0:
        raise ValueError("Amount must be positive")

    portfolio = await get_raw_portfolio(user_id)
    if portfolio is None:
        await ensure_user(user_id)
        portfolio = await get_raw_portfolio(user_id)
    assert portfolio is not None

    shares = amount / px
    holdings: list[dict] = list(portfolio.get("holdings", []))
    cash = float(portfolio.get("cash", 0))

    if trade_type == "BUY":
        if cash < amount:
            raise ValueError(f"Insufficient cash. Available: ${cash:.2f}")
        cash -= amount
        existing = next((h for h in holdings if h["stock"] == stock), None)
        if existing:
            total_cost = existing["avgCost"] * existing["shares"] + amount
            existing["shares"] += shares
            existing["avgCost"] = total_cost / existing["shares"]
            existing["currentPrice"] = px
        else:
            holdings.append(
                {
                    "stock": stock,
                    "shares": shares,
                    "avgCost": px,
                    "currentPrice": px,
                }
            )
    else:  # SELL
        existing = next((h for h in holdings if h["stock"] == stock), None)
        if not existing or existing["shares"] < shares - 1e-9:
            owned = existing["shares"] if existing else 0
            raise ValueError(f"Insufficient shares of {stock}. Owned: {owned:.4f}")
        existing["shares"] -= shares
        cash += amount
        existing["currentPrice"] = px
        if existing["shares"] < 1e-8:
            holdings = [h for h in holdings if h["stock"] != stock]

    trade = {
        "id": _oid(),
        "userId": user_id,
        "strategyId": strategy_id,
        "stock": stock,
        "type": trade_type,
        "amount": amount,
        "shares": shares,
        "price": px,
        "confidence": confidence,
        "reasoning": reasoning,
        "timestamp": _now().isoformat() if using_memory() else _now(),
    }

    history = list(portfolio.get("history", []))
    current_value = cash + sum(
        h["shares"] * get_demo_price(h["stock"]) for h in holdings
    )
    # refresh prices
    for h in holdings:
        h["currentPrice"] = get_demo_price(h["stock"])

    today = _now().date().isoformat()
    if history and history[-1].get("date") == today:
        history[-1]["value"] = current_value
    else:
        history.append({"date": today, "value": current_value})

    updated = {
        **portfolio,
        "cash": cash,
        "holdings": holdings,
        "history": history,
    }

    if using_memory():
        store = get_memory_store()
        store["portfolios"][user_id] = updated
        store["trades"].append(trade)
    else:
        db = get_db()
        assert db is not None
        await db.portfolios.update_one({"userId": user_id}, {"$set": updated})
        await db.trades.insert_one({**trade, "_id": trade["id"]})

    return trade


async def get_raw_portfolio(user_id: str) -> dict[str, Any] | None:
    if using_memory():
        return get_memory_store()["portfolios"].get(user_id)
    db = get_db()
    assert db is not None
    return await db.portfolios.find_one({"userId": user_id})


async def get_portfolio(user_id: str) -> Portfolio:
    await ensure_user(user_id)
    raw = await get_raw_portfolio(user_id)
    assert raw is not None

    holdings = []
    holdings_value = 0.0
    for h in raw.get("holdings", []):
        price = get_demo_price(h["stock"])
        holdings.append(
            Holding(
                stock=h["stock"],
                shares=h["shares"],
                avgCost=h.get("avgCost", price),
                currentPrice=price,
            )
        )
        holdings_value += h["shares"] * price

    cash = float(raw.get("cash", 0))
    starting = float(raw.get("startingBalance", get_settings().starting_cash))
    current = cash + holdings_value
    ret = ((current - starting) / starting) * 100 if starting else 0.0

    return Portfolio(
        userId=user_id,
        cash=round(cash, 2),
        holdings=holdings,
        startingBalance=starting,
        currentValue=round(current, 2),
        returnPct=round(ret, 2),
    )


async def get_portfolio_history(user_id: str) -> list[dict[str, Any]]:
    raw = await get_raw_portfolio(user_id)
    if not raw:
        return []
    return raw.get("history", [])


async def list_trades(user_id: str) -> list[dict[str, Any]]:
    if using_memory():
        trades = [t for t in get_memory_store()["trades"] if t.get("userId") == user_id]
        return sorted(trades, key=lambda t: str(t.get("timestamp")), reverse=True)
    db = get_db()
    assert db is not None
    cursor = db.trades.find({"userId": user_id}).sort("timestamp", -1)
    results = await cursor.to_list(200)
    for t in results:
        t["id"] = t.get("id") or str(t.get("_id"))
    return results
