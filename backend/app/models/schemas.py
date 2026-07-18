from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


class UserCreate(BaseModel):
    user_id: str = Field(alias="userId")
    name: str

    class Config:
        populate_by_name = True


class User(BaseModel):
    user_id: str = Field(alias="userId")
    name: str
    created_at: datetime = Field(alias="createdAt")

    class Config:
        populate_by_name = True


class StrategyCreate(BaseModel):
    description: str
    user_id: str | None = Field(default=None, alias="userId")

    class Config:
        populate_by_name = True


class StrategyRules(BaseModel):
    buy: list[str] = []
    sell: list[str] = []


class Strategy(BaseModel):
    id: str | None = None
    user_id: str = Field(alias="userId")
    name: str
    description: str
    risk_level: str = Field(alias="riskLevel")
    stocks: list[str] = []
    rules: StrategyRules
    created_at: datetime = Field(alias="createdAt")
    hash: str | None = None
    solana_signature: str | None = Field(default=None, alias="solanaSignature")
    verified: bool = False

    class Config:
        populate_by_name = True


class StockAnalyzeRequest(BaseModel):
    symbol: str
    user_id: str | None = Field(default=None, alias="userId")

    class Config:
        populate_by_name = True


class StockAnalysis(BaseModel):
    stock: str
    symbol: str
    recommendation: Literal["BUY", "HOLD", "SELL"]
    confidence: int
    reasoning: list[str] = []
    positives: list[str] = []
    risks: list[str] = []
    summary: str
    disclaimer: str = (
        "AI-assisted analysis grounded in available market data. "
        "Confidence reflects strength of the reasoning given the information — "
        "not the probability the stock will rise. Not financial advice."
    )


class TradeCreate(BaseModel):
    stock: str
    type: Literal["BUY", "SELL"]
    amount: float
    confidence: int = 0
    reasoning: str = ""
    strategy_id: str | None = Field(default=None, alias="strategyId")
    user_id: str | None = Field(default=None, alias="userId")
    price: float | None = None

    class Config:
        populate_by_name = True


class Trade(BaseModel):
    id: str | None = None
    user_id: str = Field(alias="userId")
    strategy_id: str | None = Field(default=None, alias="strategyId")
    stock: str
    type: Literal["BUY", "SELL"]
    amount: float
    shares: float = 0
    price: float = 0
    confidence: int = 0
    reasoning: str = ""
    timestamp: datetime

    class Config:
        populate_by_name = True


class Holding(BaseModel):
    stock: str
    shares: float
    avg_cost: float = Field(alias="avgCost")
    current_price: float = Field(alias="currentPrice")
    market_value: float = Field(default=0.0, alias="marketValue")
    cost_basis: float = Field(default=0.0, alias="costBasis")
    unrealized_pnl: float = Field(default=0.0, alias="unrealizedPnl")
    unrealized_pnl_pct: float = Field(default=0.0, alias="unrealizedPnlPct")
    last_purchase_price: float | None = Field(default=None, alias="lastPurchasePrice")

    class Config:
        populate_by_name = True


class Portfolio(BaseModel):
    user_id: str = Field(alias="userId")
    cash: float
    holdings: list[Holding] = []
    starting_balance: float = Field(default=10000.0, alias="startingBalance")
    current_value: float = Field(default=10000.0, alias="currentValue")
    return_pct: float = Field(default=0.0, alias="returnPct")
    invested_value: float = Field(default=0.0, alias="investedValue")
    total_cost_basis: float = Field(default=0.0, alias="totalCostBasis")
    unrealized_pnl: float = Field(default=0.0, alias="unrealizedPnl")
    unrealized_pnl_pct: float = Field(default=0.0, alias="unrealizedPnlPct")
    last_marked_at: str | None = Field(default=None, alias="lastMarkedAt")
    simulated: bool = True

    class Config:
        populate_by_name = True


class PredictionRequest(BaseModel):
    market: str
    question: str
    context: str = ""
    user_id: str | None = Field(default=None, alias="userId")

    class Config:
        populate_by_name = True


class PredictionResult(BaseModel):
    market: str
    question: str
    prediction: Literal["YES", "NO"]
    confidence: int
    reasoning: list[str] = []
    risks: list[str] = []
    disclaimer: str = "AI-assisted prediction market analysis. Not a guarantee of outcome."
