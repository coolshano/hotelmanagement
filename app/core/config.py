from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


def _read_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./data/hotel.db",
    )

    redis_url: str = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0",
    )

    secret_key: str = os.getenv(
        "HMS_SECRET_KEY",
        "local-development-secret-change-before-deployment",
    )

    access_token_minutes: int = int(
        os.getenv("HMS_ACCESS_TOKEN_MINUTES", "15")
    )

    refresh_token_days: int = int(
        os.getenv("HMS_REFRESH_TOKEN_DAYS", "7")
    )

    tax_rate: float = float(
        os.getenv("HMS_TAX_RATE", "0.12")
    )

    currency: str = os.getenv(
        "HMS_CURRENCY",
        "GBP",
    )

    reset_database: bool = _read_bool(
        "HMS_RESET_DATABASE"
    )

    allowed_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "HMS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    )

    # Email Settings
    smtp_host: str = os.getenv(
        "SMTP_HOST",
        "smtp.gmail.com",
    )

    smtp_port: int = int(
        os.getenv("SMTP_PORT", "587")
    )

    smtp_username: str = os.getenv(
        "SMTP_USERNAME",
        "",
    )

    smtp_password: str = os.getenv(
        "SMTP_PASSWORD",
        "",
    )

    smtp_from_email: str = os.getenv(
        "SMTP_FROM_EMAIL",
        "",
    )

    smtp_from_name: str = os.getenv(
        "SMTP_FROM_NAME",
        "Royal Crest Hotel",
    )


settings = Settings()