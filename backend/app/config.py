"""Application settings loaded from environment variables."""

import logging

from pydantic_settings import BaseSettings

log = logging.getLogger(__name__)

_DEFAULT_SECRET = "dev-secret-change-in-production"


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://gpsa:gpsa@localhost:5432/gpsa"
    secret_key: str = _DEFAULT_SECRET
    access_token_expire_minutes: int = 480  # 8 hours (covers full event day)
    dev_mode: bool = True
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    model_config = {
        "env_prefix": "GPSA_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def check_security(self) -> None:
        """Warn or raise on insecure configuration."""
        if self.dev_mode:
            log.warning(
                "\n" + "=" * 60 + "\n"
                "  DEV_MODE is ON — seed data will be loaded.\n"
                "  DO NOT use DEV_MODE=true in production.\n" + "=" * 60
            )
        if self.secret_key == _DEFAULT_SECRET:
            if not self.dev_mode:
                raise RuntimeError(
                    "GPSA_SECRET_KEY is still the default value. "
                    "Set a strong GPSA_SECRET_KEY environment variable for production."
                )
            log.warning("Using default SECRET_KEY — acceptable for development only.")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
