from fastapi import APIRouter, Depends

from app.auth import get_current_user, user_id_from
from app.models.schemas import StockAnalyzeRequest
from app.services.gemini_service import gemini_service
from app.services.market_data_service import get_quote
from app.services import portfolio_service as ps

router = APIRouter(prefix="/stock", tags=["stock"])


@router.post("/analyze")
async def analyze_stock(
    body: StockAnalyzeRequest,
    user: dict = Depends(get_current_user),
):
    uid = user_id_from(user, body.user_id)
    await ps.ensure_user(uid, user.get("name", "Trader"))

    quote = await get_quote(body.symbol)
    market = quote.to_api()
    analysis = await gemini_service.analyze_stock(body.symbol, market_context=market)

    return {
        "analysis": analysis,
        "market": market,
        "disclaimer": "AI-assisted analysis. Potential opportunity and risk assessment only — never a certainty.",
    }


@router.get("/quote/{symbol}")
async def stock_quote(symbol: str, user: dict = Depends(get_current_user)):
    """Live (or fallback) quote for paper-trading fills and research UI."""
    _ = user
    quote = await get_quote(symbol)
    return {"quote": quote.to_api()}
