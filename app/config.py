import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _build_database_url() -> str:
    """Return the PostgreSQL database URL used by SQLModel.

    Primary option:
    - DATABASE_URL=postgresql+psycopg://user:password@host:port/db

    Fallback option, compatible with DB_* environment variables:
    - DB_USER
    - DB_PASSWORD
    - DB_HOST
    - DB_PORT
    - DB_NAME
    """

    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return database_url

    db_user = os.getenv("DB_USER", "termini")
    db_password = os.getenv("DB_PASSWORD", "termini")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "termini_db")

    return f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    app_name: str = "Termini konzultacija / prijava na laboratorij"
    database_url: str = _build_database_url()
    secret_key: str = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )


settings = Settings()
