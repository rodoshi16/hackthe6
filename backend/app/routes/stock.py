from fastapi import APIRouter, Depends

from app.auth import get_current_user, user_id_from
from app.models.schemas import StockAnalyzeRequest
from app.services.gemini_service import gemini_service
from app.services import portfolio_service as ps

router = APIRouter(prefix="/stock", tags=["stock"])


@router.post("/analyze")
async def analyze_stock(
    body: StockAnalyzeRequest,
    user: dict = Depends(get_current_user),
):
    uid = user_id_from(user, body.user_id)
    await ps.ensure_user(uid, user.get("name", "Trader"))
    analysis = await gemini_service.analyze_stock(body.symbol)
    return {
        "analysis": analysis,
        "disclaimer": "AI-assisted analysis. Potential opportunity and risk assessment only — never a certainty.",
    }
