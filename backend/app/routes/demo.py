"""Demo seed — populates a full paper desk for hackathon walkthroughs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.auth import get_current_user, user_id_from
from app.database.connection import get_memory_store, using_memory, get_db
from app.services.market_data_service import get_quote, bump_demo_prices
from app.services.solana_service import verify_on_solana
from app.services import portfolio_service as ps

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/seed")
async def seed_demo_desk(user: dict = Depends(get_current_user)):
    """
    Reset the current user to a rich demo state:
    strategy + Solana hash, holdings with unrealized P&L, trade history, growth chart.
    Uses live prices when available; demo marks otherwise.
    """
    uid = user_id_from(user)
    await ps.ensure_user(uid, user.get("name", "Demo Trader"))

    # Keep offline demo bumps available if market APIs fail mid-seed
    bump_demo_prices(
        {
            "NVDA": 1.085,
            "MSFT": 1.032,
            "AMD": 0.97,
            "GOOG": 1.041,
        }
    )

    nvda_q = await get_quote("NVDA")
    msft_q = await get_quote("MSFT")
    nvda_px = nvda_q.price
    msft_px = msft_q.price
    # Cost basis ~8% below mark so the desk shows green P&L for walkthroughs
    nvda_cost = round(nvda_px * 0.92, 2)
    msft_cost = round(msft_px * 0.96, 2)

    now = datetime.now(timezone.utc)
    strategy_doc = {
        "userId": uid,
        "name": "AI Growth Momentum",
        "description": "Medium-risk strategy focused on AI companies.",
        "riskLevel": "Medium",
        "stocks": ["NVDA", "MSFT", "AMD", "GOOG"],
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
        "createdAt": (now - timedelta(days=5)).isoformat(),
    }
    verification = await verify_on_solana(strategy_doc)
    strategy_doc.update(
        {
            "hash": verification["hash"],
            "solanaSignature": verification["solanaSignature"],
            "verified": True,
            "network": verification["network"],
        }
    )
    strategy = await ps.save_strategy(strategy_doc)

    holdings = [
        {
            "stock": "NVDA",
            "shares": 12.0,
            "avgCost": nvda_cost,
            "currentPrice": nvda_px,
        },
        {
            "stock": "MSFT",
            "shares": 4.0,
            "avgCost": msft_cost,
            "currentPrice": msft_px,
        },
    ]
    cash = 4200.0
    holdings_value = sum(h["shares"] * h["currentPrice"] for h in holdings)
    current = cash + holdings_value
    starting = 10000.0

    history = []
    for i in range(7):
        day = (now - timedelta(days=6 - i)).date().isoformat()
        t = i / 6
        value = round(starting + (current - starting) * (t**1.15), 2)
        history.append({"date": day, "value": value})

    trades = [
        {
            "id": "seed-trade-1",
            "userId": uid,
            "strategyId": strategy.get("id"),
            "stock": "NVDA",
            "type": "BUY",
            "amount": round(8 * nvda_cost, 2),
            "shares": 8.0,
            "price": nvda_cost,
            "confidence": 82,
            "reasoning": "AI-assisted analysis: chip demand + momentum. Potential opportunity with valuation risk.",
            "timestamp": (now - timedelta(days=5)).isoformat(),
        },
        {
            "id": "seed-trade-2",
            "userId": uid,
            "strategyId": strategy.get("id"),
            "stock": "MSFT",
            "type": "BUY",
            "amount": round(4 * msft_cost, 2),
            "shares": 4.0,
            "price": msft_cost,
            "confidence": 78,
            "reasoning": "Cloud + Copilot monetization runway; diversified enterprise base.",
            "timestamp": (now - timedelta(days=3)).isoformat(),
        },
        {
            "id": "seed-trade-3",
            "userId": uid,
            "strategyId": strategy.get("id"),
            "stock": "NVDA",
            "type": "BUY",
            "amount": round(4 * nvda_cost, 2),
            "shares": 4.0,
            "price": nvda_cost,
            "confidence": 80,
            "reasoning": "Added on strategy rule: increasing momentum with positive sentiment.",
            "timestamp": (now - timedelta(days=1)).isoformat(),
        },
    ]

    portfolio = {
        "userId": uid,
        "cash": cash,
        "holdings": holdings,
        "startingBalance": starting,
        "history": history,
    }

    if using_memory():
        store = get_memory_store()
        store["portfolios"][uid] = portfolio
        store["trades"] = [t for t in store["trades"] if t.get("userId") != uid] + trades
    else:
        db = get_db()
        assert db is not None
        await db.portfolios.update_one({"userId": uid}, {"$set": portfolio}, upsert=True)
        await db.trades.delete_many({"userId": uid})
        for t in trades:
            await db.trades.insert_one({**t, "_id": t["id"]})

    portfolio_view = await ps.get_portfolio(uid)
    return {
        "ok": True,
        "message": "Demo desk loaded — strategy, trades, and portfolio ready for walkthrough.",
        "strategy": strategy,
        "verification": verification,
        "portfolio": portfolio_view,
        "trades": trades,
        "marketSource": {"NVDA": nvda_q.source, "MSFT": msft_q.source},
    }
