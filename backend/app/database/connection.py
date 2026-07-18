from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import get_settings

client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None

# In-memory fallback store for demo without MongoDB
_memory_store: dict = {
    "users": {},
    "strategies": {},
    "trades": [],
    "portfolios": {},
}


def get_memory_store() -> dict:
    return _memory_store


async def connect_db() -> None:
    global client, db
    settings = get_settings()
    try:
        client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
        await client.admin.command("ping")
        db = client[settings.mongodb_db]
        print(f"Connected to MongoDB: {settings.mongodb_db}")
    except Exception as e:
        print(f"MongoDB unavailable ({e}). Using in-memory store for demo.")
        client = None
        db = None


async def close_db() -> None:
    global client, db
    if client:
        client.close()
        client = None
        db = None


def get_db() -> AsyncIOMotorDatabase | None:
    return db


def using_memory() -> bool:
    return db is None
