"""Central configuration, loaded once from the environment.

Import `settings` anywhere: `from app.config import settings`.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    env: str = "development"
    debug: bool = True
    secret_key: str = "change-me"

    # Database
    postgres_user: str = "carma"
    postgres_password: str = "carma"
    postgres_db: str = "carma"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # WhatsApp
    whatsapp_phone_number_id: str = ""
    whatsapp_waba_id: str = ""
    whatsapp_token: str = ""
    whatsapp_verify_token: str = "carma-verify-me"
    whatsapp_app_secret: str = ""
    whatsapp_session_minutes: int = 30
    ai_message_limit: int = 15

    # Payments
    payment_provider: str = "stripe"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""
    report_price_soles: float = 29.90
    currency: str = "PEN"

    # RPA / cost control
    captcha_api_key: str = ""
    captcha_provider: str = "2captcha"
    rpa_paid_cost_soles: float = 6.10
    rpa_timeout_seconds: int = 45
    rpa_max_concurrency: int = 7

    # AI
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-5"
    llm_max_tokens: int = 1024

    # Support
    support_email: str = "soporte@carma.pe"
    public_base_url: str = "https://api.carma.pe"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
