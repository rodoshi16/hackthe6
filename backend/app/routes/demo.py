"""Demo seed — populates a full paper desk for hackathon walkthroughs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.auth import get_current_user, user_id_from
from app.database.connection import get_memory_store, using_memory, get_db
from app.services.gemini_service import get_demo_price, bump_demo_prices
from app.services.solana_service import verify_on_solana
from app.services import portfolio_service as ps

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/seed")
async def seed_demo_desk(user: dict = Depends(get_current_user)):
    """
    Reset the current user to a rich demo state:
    strategy + Solana hash, holdings with unrealized P&L, trade history, growth chart.
    """
    uid = user_id_from(user)
    await ps.ensure_user(uid, user.get("name", "Demo Trader"))

    # Mark prices up so holdings show green P&L
    bump_demo_prices(
        {
            "NVDA": 1.085,
            "MSFT": 1.032,
            "AMD": 0.97,
            "GOOG": 1.041,
        }
    )

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

    # Build portfolio with cost basis below current mark
    nvda_cost = 118.40
    msft_cost = 412.00
    holdings = [
        {
            "stock": "NVDA",
            "shares": 12.0,
            "avgCost": nvda_cost,
            "currentPrice": get_demo_price("NVDA"),
        },
        {
            "stock": "MSFT",
            "shares": 4.0,
            "avgCost": msft_cost,
            "currentPrice": get_demo_price("MSFT"),
        },
    ]
    cash = 4200.0
    holdings_value = sum(h["shares"] * get_demo_price(h["stock"]) for h in holdings)
    current = cash + holdings_value
    starting = 10000.0

    history = []
    for i in range(7):
        day = (now - timedelta(days=6 - i)).date().isoformat()
        # Smooth climb from starting → current
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
        # Replace this user's trades
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
    }
