"""Predict the 6ix — adapt AlphaAI strategy engine to prediction markets."""

from fastapi import APIRouter, Depends

from app.auth import get_current_user, user_id_from
from app.models.schemas import PredictionRequest
from app.services.gemini_service import gemini_service
from app.services import portfolio_service as ps

router = APIRouter(prefix="/predict", tags=["predict-the-6ix"])


@router.post("/analyze")
async def analyze_prediction(
    body: PredictionRequest,
    user: dict = Depends(get_current_user),
):
    """
    Same AI engine as stock analysis, adapted for YES/NO prediction markets.
    Built for Hack the 6ix "Best Predict the 6ix Trading Bot".
    """
    uid = user_id_from(user, body.user_id)
    await ps.ensure_user(uid, user.get("name", "Trader"))

    result = await gemini_service.predict_market(
        market=body.market,
        question=body.question,
        context=body.context,
    )

    # Map to strategy-like rules for consistency with the stock engine
    rules = {
        "enter": [
            "Favorable base-rate evidence",
            "Narrative catalysts aligned with predicted side",
            "Market liquidity supports position sizing",
        ],
        "exit": [
            "Sudden news invalidates thesis",
            "Implied probability diverges from model confidence",
            "Risk limits breached",
        ],
    }

    return {
        "prediction": result,
        "engine": "alphaai-predict-the-6ix",
        "adaptedFrom": "stock-strategy-engine",
        "rules": rules,
        "disclaimer": result.disclaimer,
    }


@router.get("/markets")
async def list_demo_markets():
    """Sample Predict the 6ix style markets for the demo."""
    return {
        "markets": [
            {
                "id": "ht6-keynote",
                "market": "Hack the 6ix 2026",
                "question": "Will attendance exceed last year's Hack the 6ix?",
                "category": "Events",
            },
            {
                "id": "ai-reg",
                "market": "AI Regulation",
                "question": "Will Canada announce new AI safety guidelines in 2026?",
                "category": "Policy",
            },
            {
                "id": "tsx-tech",
                "market": "TSX Tech",
                "question": "Will Canadian tech stocks outperform the TSX Composite this quarter?",
                "category": "Markets",
            },
            {
                "id": "btc-100k",
                "market": "Crypto",
                "question": "Will Bitcoin trade above $100,000 before year end?",
                "category": "Crypto",
            },
        ]
    }
