from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://ai_maliyet_user:change_me@localhost:5432/ai_maliyet_merkezi"
    app_env: str = "dev"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    raw_dir: str = str(ROOT / "data" / "raw")
    http_timeout: float = 30.0
    http_retries: int = 3
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    fx_endpoint: str = "https://api.frankfurter.app/latest?from=USD&to=TRY"


settings = Settings()
