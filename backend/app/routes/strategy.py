from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, user_id_from
from app.models.schemas import StrategyCreate, StrategyRules
from app.services.gemini_service import gemini_service
from app.services.solana_service import verify_on_solana
from app.services import portfolio_service as ps

router = APIRouter(prefix="/strategy", tags=["strategy"])


@router.post("/create")
async def create_strategy(
    body: StrategyCreate,
    user: dict = Depends(get_current_user),
):
    uid = user_id_from(user, body.user_id)
    await ps.ensure_user(uid, user.get("name", "Trader"))

    generated = await gemini_service.generate_strategy(body.description)
    rules_raw = generated.get("rules", {})
    rules = StrategyRules(
        buy=rules_raw.get("buy", []),
        sell=rules_raw.get("sell", []),
    )

    now = datetime.now(timezone.utc)
    strategy_doc = {
        "userId": uid,
        "name": generated["name"],
        "description": generated.get("summary") or body.description,
        "riskLevel": generated["riskLevel"],
        "stocks": generated["stocks"],
        "rules": {"buy": rules.buy, "sell": rules.sell},
        "createdAt": now.isoformat(),
        "hash": None,
        "solanaSignature": None,
        "verified": False,
    }

    # Blockchain verification layer
    verification = await verify_on_solana(strategy_doc)
    strategy_doc["hash"] = verification["hash"]
    strategy_doc["solanaSignature"] = verification["solanaSignature"]
    strategy_doc["verified"] = verification["verified"]
    strategy_doc["network"] = verification["network"]

    saved = await ps.save_strategy(strategy_doc)
    return {
        "strategy": saved,
        "verification": verification,
        "disclaimer": "AI-assisted strategy for paper trading only. Not financial advice.",
    }


@router.get("/list")
async def list_strategies(user: dict = Depends(get_current_user)):
    uid = user_id_from(user)
    await ps.ensure_user(uid, user.get("name", "Trader"))
    strategies = await ps.list_strategies(uid)
    return {"strategies": strategies}


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: str, user: dict = Depends(get_current_user)):
    strategy = await ps.get_strategy(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"strategy": strategy}
