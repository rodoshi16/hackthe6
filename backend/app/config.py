from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "alphaai"
    gemini_api_key: str = ""
    auth0_domain: str = ""
    auth0_audience: str = ""
    auth0_algorithms: str = "RS256"
    cors_origins: str = "http://localhost:5173"
    starting_cash: float = 10000.0
    solana_rpc_url: str = "https://api.devnet.solana.com"
    demo_mode: bool = True  # use mock AI/DB when keys missing


@lru_cache
def get_settings() -> Settings:
    return Settings()
