import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    app_name: str = "Termini konzultacija / prijava na laboratorij"
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://termini:termini@localhost:5432/termini_db",
    )
    secret_key: str = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )


settings = Settings()
