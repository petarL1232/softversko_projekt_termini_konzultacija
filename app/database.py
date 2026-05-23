from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = create_engine(settings.database_url, echo=False)


def create_db_and_tables() -> None:
    """Create database tables for local development/demo.

    Do not leave this as pass: FastAPI calls it on startup, and without it the
    app has no tables in a fresh PostgreSQL database.
    """

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a database session."""

    with Session(engine) as session:
        yield session
