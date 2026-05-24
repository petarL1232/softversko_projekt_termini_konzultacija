import pytest
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool


@pytest.fixture(name="session")
def session_fixture():
    """Provide a clean test database session for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

        # Cleanup after each test
        try:
            session.exec(text("DELETE FROM term_registrations"))
            session.exec(text("DELETE FROM consultation_terms"))
            session.exec(text("DELETE FROM subjects"))
            session.exec(text("DELETE FROM users"))
            session.exec(text("DELETE FROM offices"))
            session.commit()
        except Exception:
            session.rollback()
