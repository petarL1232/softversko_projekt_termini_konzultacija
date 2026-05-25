import os
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

load_dotenv()


def build_database_url() -> str:
    """Build the PostgreSQL connection URL.

    Priority:
    1. DATABASE_URL, useful for Docker and CI.
    2. DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME, useful for local .env files.
    3. Safe Docker-compose default for this project.
    """

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    db_user = os.getenv("DB_USER", "termini")
    db_password = os.getenv("DB_PASSWORD", "termini")
    db_host = os.getenv("DB_HOST", "db")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "termini_db")

    return f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


DATABASE_URL = build_database_url()
engine = create_engine(DATABASE_URL)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def run_trigger_sql() -> None:
    """Run optional PostgreSQL trigger definitions.

    This file adapts the SQL trigger work to the existing Python models.
    It is safe to call multiple times because sql/trigger.sql is idempotent.
    """

    trigger_path = Path(__file__).resolve().parent.parent / "sql" / "trigger.sql"

    if not trigger_path.exists():
        return

    sql_script = trigger_path.read_text(encoding="utf-8")

    connection = engine.raw_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql_script)
        connection.commit()
    finally:
        connection.close()


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    run_trigger_sql()


def create_default_admin() -> None:
    """Create a demo admin compatible with the existing auth flow."""

    from app.models import User, UserRole
    from app.services.security import hash_password

    with Session(engine) as session:
        admin = session.query(User).filter_by(email="admin@example.com").first()
        if not admin:
            admin = User(
                first_name="Admin",
                last_name="User",
                email="admin@example.com",
                password_hash=hash_password("admin"),
                role=UserRole.ADMIN,
                office_id=None,
            )
            session.add(admin)
            session.commit()
