"""Paper trading engine — simulated fills only (fake money).

BUY/SELL:
  1. Fetch latest market price (fresh quote, not stale cache)
  2. Calculate shares from dollar amount
  3. Persist purchase/sale price on the trade + holding cost basis
  4. Update cash & holdings
  5. Mark positions to market for unrealized P&L

Dashboard / GET portfolio:
  Re-marks every holding with live prices and updates stored marks + history.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings
from app.database.connection import get_db, get_memory_store, using_memory
from app.models.schemas import Holding, Portfolio
from app.services.market_data_service import get_price, get_prices, get_quote


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _oid() -> str:
    return str(uuid.uuid4())


def _round_money(value: float) -> float:
    return round(float(value), 2)


def _round_shares(value: float) -> float:
    return round(float(value), 8)


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


async def get_raw_portfolio(user_id: str) -> dict[str, Any] | None:
    if using_memory():
        return get_memory_store()["portfolios"].get(user_id)
    db = get_db()
    assert db is not None
    return await db.portfolios.find_one({"userId": user_id})


async def _persist_portfolio(user_id: str, portfolio: dict[str, Any]) -> None:
    if using_memory():
        get_memory_store()["portfolios"][user_id] = portfolio
    else:
        db = get_db()
        assert db is not None
        await db.portfolios.update_one({"userId": user_id}, {"$set": portfolio}, upsert=True)


def _holding_metrics(
    stock: str,
    shares: float,
    avg_cost: float,
    current_price: float,
    last_purchase_price: float | None = None,
) -> Holding:
    shares = float(shares)
    avg_cost = float(avg_cost)
    current_price = float(current_price)
    cost_basis = shares * avg_cost
    market_value = shares * current_price
    unrealized = market_value - cost_basis
    unrealized_pct = (unrealized / cost_basis * 100) if cost_basis else 0.0
    return Holding(
        stock=stock,
        shares=_round_shares(shares),
        avgCost=_round_money(avg_cost),
        currentPrice=_round_money(current_price),
        marketValue=_round_money(market_value),
        costBasis=_round_money(cost_basis),
        unrealizedPnl=_round_money(unrealized),
        unrealizedPnlPct=round(unrealized_pct, 2),
        lastPurchasePrice=_round_money(last_purchase_price)
        if last_purchase_price is not None
        else None,
    )


async def execute_trade(
    user_id: str,
    stock: str,
    trade_type: str,
    amount: float,
    confidence: int = 0,
    reasoning: str = "",
    strategy_id: str | None = None,
    price: float | None = None,  # ignored for fills — always use live market mark
) -> dict[str, Any]:
    """Execute a simulated paper trade at the latest market price."""
    _ = price  # client hints are not used for fills
    stock = stock.upper().strip()
    if not stock:
        raise ValueError("Stock symbol is required")
    if amount <= 0:
        raise ValueError("Amount must be positive")
    if trade_type not in {"BUY", "SELL"}:
        raise ValueError("Trade type must be BUY or SELL")

    # Fresh quote for paper fill
    quote = await get_quote(stock, use_cache=False)
    fill_price = float(quote.price)
    if fill_price <= 0:
        raise ValueError(f"Unable to obtain a valid market price for {stock}")

    portfolio = await get_raw_portfolio(user_id)
    if portfolio is None:
        await ensure_user(user_id)
        portfolio = await get_raw_portfolio(user_id)
    assert portfolio is not None

    shares = _round_shares(amount / fill_price)
    if shares <= 0:
        raise ValueError("Share quantity too small")

    holdings: list[dict] = [dict(h) for h in portfolio.get("holdings", [])]
    cash = float(portfolio.get("cash", 0))
    # Spend/receive exact dollar amount for bookkeeping clarity
    notional = _round_money(amount)

    if trade_type == "BUY":
        if cash + 1e-9 < notional:
            raise ValueError(f"Insufficient cash. Available: ${cash:.2f}")
        cash = _round_money(cash - notional)
        existing = next((h for h in holdings if h["stock"] == stock), None)
        if existing:
            prev_shares = float(existing["shares"])
            prev_cost = float(existing.get("avgCost", fill_price)) * prev_shares
            new_shares = prev_shares + shares
            existing["shares"] = _round_shares(new_shares)
            existing["avgCost"] = _round_money((prev_cost + notional) / new_shares)
            existing["currentPrice"] = fill_price
            existing["lastPurchasePrice"] = fill_price
        else:
            holdings.append(
                {
                    "stock": stock,
                    "shares": shares,
                    "avgCost": fill_price,
                    "currentPrice": fill_price,
                    "lastPurchasePrice": fill_price,
                }
            )
    else:  # SELL
        existing = next((h for h in holdings if h["stock"] == stock), None)
        owned = float(existing["shares"]) if existing else 0.0
        if not existing or owned + 1e-9 < shares:
            raise ValueError(f"Insufficient shares of {stock}. Owned: {owned:.4f}")
        # Proceeds from selling the calculated share count at live mark
        proceeds = _round_money(shares * fill_price)
        existing["shares"] = _round_shares(owned - shares)
        cash = _round_money(cash + proceeds)
        existing["currentPrice"] = fill_price
        notional = proceeds
        if existing["shares"] < 1e-8:
            holdings = [h for h in holdings if h["stock"] != stock]

    trade = {
        "id": _oid(),
        "userId": user_id,
        "strategyId": strategy_id,
        "stock": stock,
        "type": trade_type,
        "amount": notional,
        "shares": shares,
        "price": fill_price,
        "purchasePrice": fill_price if trade_type == "BUY" else None,
        "confidence": confidence,
        "reasoning": reasoning,
        "simulated": True,
        "priceSource": quote.source,
        "companyName": quote.company_name,
        "timestamp": _now().isoformat() if using_memory() else _now(),
    }

    # Mark all holdings to current market for unrealized P&L snapshot
    marks = await get_prices([h["stock"] for h in holdings], use_cache=True)
    for h in holdings:
        mark = marks.get(h["stock"], float(h.get("currentPrice") or fill_price))
        h["currentPrice"] = mark

    marked_at = _now().isoformat()
    holdings_value = sum(float(h["shares"]) * float(h["currentPrice"]) for h in holdings)
    current_value = _round_money(cash + holdings_value)

    history = list(portfolio.get("history", []))
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
        "lastMarkedAt": marked_at,
    }
    await _persist_portfolio(user_id, updated)

    if using_memory():
        get_memory_store()["trades"].append(trade)
    else:
        db = get_db()
        assert db is not None
        await db.trades.insert_one({**trade, "_id": trade["id"]})

    return trade


async def get_portfolio(user_id: str, *, persist_marks: bool = True) -> Portfolio:
    """Load portfolio and mark holdings to live market prices."""
    await ensure_user(user_id)
    raw = await get_raw_portfolio(user_id)
    assert raw is not None

    raw_holdings = [dict(h) for h in raw.get("holdings", [])]
    symbols = [h["stock"] for h in raw_holdings]
    # Fresh marks when the dashboard loads
    marks = await get_prices(symbols, use_cache=False) if symbols else {}
    marked_at = _now().isoformat()

    holdings: list[Holding] = []
    holdings_value = 0.0
    total_cost = 0.0
    persisted: list[dict] = []

    for h in raw_holdings:
        stock = h["stock"]
        shares = float(h["shares"])
        avg_cost = float(h.get("avgCost") or h.get("lastPurchasePrice") or 0)
        current = float(marks.get(stock) or h.get("currentPrice") or avg_cost or 0)
        if current <= 0:
            current = await get_price(stock, use_cache=False)

        metrics = _holding_metrics(
            stock=stock,
            shares=shares,
            avg_cost=avg_cost,
            current_price=current,
            last_purchase_price=h.get("lastPurchasePrice"),
        )
        holdings.append(metrics)
        holdings_value += metrics.market_value
        total_cost += metrics.cost_basis
        persisted.append(
            {
                "stock": stock,
                "shares": metrics.shares,
                "avgCost": metrics.avg_cost,
                "currentPrice": metrics.current_price,
                "lastPurchasePrice": metrics.last_purchase_price,
            }
        )

    cash = float(raw.get("cash", 0))
    starting = float(raw.get("startingBalance", get_settings().starting_cash))
    current_value = _round_money(cash + holdings_value)
    ret = ((current_value - starting) / starting) * 100 if starting else 0.0
    unrealized = _round_money(holdings_value - total_cost)
    unrealized_pct = round((unrealized / total_cost * 100) if total_cost else 0.0, 2)

    if persist_marks:
        history = list(raw.get("history", []))
        today = _now().date().isoformat()
        if history and history[-1].get("date") == today:
            history[-1]["value"] = current_value
        else:
            history.append({"date": today, "value": current_value})
        await _persist_portfolio(
            user_id,
            {
                **raw,
                "cash": cash,
                "holdings": persisted,
                "history": history,
                "lastMarkedAt": marked_at,
            },
        )

    return Portfolio(
        userId=user_id,
        cash=_round_money(cash),
        holdings=holdings,
        startingBalance=starting,
        currentValue=current_value,
        returnPct=round(ret, 2),
        investedValue=_round_money(holdings_value),
        totalCostBasis=_round_money(total_cost),
        unrealizedPnl=unrealized,
        unrealizedPnlPct=unrealized_pct,
        lastMarkedAt=marked_at,
        simulated=True,
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
