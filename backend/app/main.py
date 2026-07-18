from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database.connection import connect_db, close_db
from app.routes import strategy, stock, trade, predict, demo


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await connect_db()
    yield
    await close_db()


settings = get_settings()
app = FastAPI(
    title="AlphaAI API",
    description="AI-powered stock research and paper trading platform",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(strategy.router)
app.include_router(stock.router)
app.include_router(trade.router)
app.include_router(predict.router)
app.include_router(demo.router)


@app.get("/")
async def root():
    return {
        "name": "AlphaAI",
        "status": "online",
        "docs": "/docs",
        "message": "AI stock research & paper trading — not financial advice.",
    }


@app.get("/health")
async def health():
    return {"ok": True}
