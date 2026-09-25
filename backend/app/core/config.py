from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Hôtel Gérard et Francine API"
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    app_secret_key: str = Field(min_length=32)
    access_token_expire_minutes: int = Field(default=480, gt=0)

    database_url: str

    cors_origins: list[str] = []

    media_root: Path = Path("media")
    media_url: str = "/media"
    max_upload_mb: int = Field(default=15, gt=0, le=50)


@lru_cache
def get_settings() -> Settings:
    return Settings()
