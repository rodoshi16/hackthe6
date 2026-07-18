from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, user_id_from
from app.models.schemas import TradeCreate
from app.services import portfolio_service as ps

router = APIRouter(tags=["trading"])


@router.post("/trade")
async def create_trade(
    body: TradeCreate,
    user: dict = Depends(get_current_user),
):
    uid = user_id_from(user, body.user_id)
    await ps.ensure_user(uid, user.get("name", "Trader"))

    try:
        trade = await ps.execute_trade(
            user_id=uid,
            stock=body.stock,
            trade_type=body.type,
            amount=body.amount,
            confidence=body.confidence,
            reasoning=body.reasoning,
            strategy_id=body.strategy_id,
            price=body.price,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    portfolio = await ps.get_portfolio(uid)
    return {
        "trade": trade,
        "portfolio": portfolio,
        "explanation": {
            "decision": f"{body.type} {body.stock.upper()}",
            "confidence": body.confidence,
            "why": body.reasoning
            or "Paper trade executed based on user instruction with AI context.",
            "note": "Simulated trade with fake money. Explainable AI decision trail recorded.",
        },
    }


@router.get("/trades")
async def get_trades(user: dict = Depends(get_current_user)):
    uid = user_id_from(user)
    await ps.ensure_user(uid, user.get("name", "Trader"))
    trades = await ps.list_trades(uid)
    return {"trades": trades}


@router.get("/portfolio")
async def get_portfolio(user: dict = Depends(get_current_user)):
    uid = user_id_from(user)
    await ps.ensure_user(uid, user.get("name", "Trader"))
    portfolio = await ps.get_portfolio(uid)
    history = await ps.get_portfolio_history(uid)
    return {"portfolio": portfolio, "history": history}
