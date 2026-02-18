"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./symposium.db"
    secret_key: str = "dev-secret-change-in-production"
    access_token_expire_minutes: int = 480  # 8 hours (covers full event day)
    dev_mode: bool = True

    model_config = {"env_prefix": "SYMPOSIUM_"}


settings = Settings()
