import os
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

load_dotenv()


def build_database_url() -> str:

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
    trigger_path = Path(__file__).resolve().parent.parent / "sql" / "trigger.sql"

    if not trigger_path.exists():
        return

    sql_script = trigger_path.read_text(encoding="utf-8")

    with engine.raw_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql_script)

        connection.commit()


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    run_trigger_sql()
