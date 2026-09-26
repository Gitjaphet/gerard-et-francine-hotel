from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
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

    hotel_timezone: str = "Indian/Antananarivo"

    email_backend: Literal["console", "smtp"] = "console"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    email_from: str = ""
    email_from_name: str = "Hôtel Gérard et Francine"
    reception_email: str = ""
    admin_base_url: str = "http://localhost:3000/admin"

    @model_validator(mode="after")
    def check_smtp_settings(self) -> Self:
        if self.email_backend == "smtp":
            missing = [
                name
                for name in ("smtp_username", "email_from", "reception_email")
                if not getattr(self, name)
            ]
            if not self.smtp_password.get_secret_value():
                missing.append("smtp_password")
            if missing:
                raise ValueError(f"Envoi SMTP activé, réglages manquants : {', '.join(missing)}")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
