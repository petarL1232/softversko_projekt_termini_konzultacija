# Ivano ima bolju bazu već tako da ovo se samo može pogledati kratko
"""Demo seed data for local development.

Pokretanje preko Dockera:
    docker compose exec app python -m app.seed

Pokretanje lokalno:
    python -m app.seed

Ovaj file je namjerno jednostavan. Sljedeci korak je da osoba zaduzena za
modele/bazu prilagodi seed stvarnoj strukturi modela ako se ona promijeni.
"""

from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.models import Termin, User, UserRole
from app.services.security import hash_password

DEMO_USERS = [
    ("admin@example.com", "admin123", UserRole.ADMIN),
    ("student1@example.com", "test123", UserRole.USER),
    ("student2@example.com", "test123", UserRole.USER),
    ("student3@example.com", "test123", UserRole.USER),
]

DEMO_TERMINI = [
    ("Konzultacije iz Matematike", "Pitanja za zadatke i kolokvij", 2, 1),
    ("Laboratorij iz Programiranja", "Grupa A", 3, 2),
    ("Konzultacije iz Baza podataka", "SQL, normalizacija i projekt", 5, 3),
]


def seed_demo_data() -> None:
    """Insert demo users and terms if they do not already exist."""

    create_db_and_tables()

    with Session(engine) as session:
        admin_id: int | None = None

        for email, password, role in DEMO_USERS:
            existing_user = session.exec(
                select(User).where(User.email == email)
            ).first()
            if existing_user is None:
                user = User(
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                existing_user = user

            if role == UserRole.ADMIN:
                admin_id = existing_user.id

        if admin_id is None:
            raise RuntimeError("Admin korisnik nije kreiran.")

        now = datetime.now(UTC)

        for naziv, opis, kapacitet, day_offset in DEMO_TERMINI:
            existing_termin = session.exec(
                select(Termin).where(Termin.naziv == naziv)
            ).first()
            if existing_termin is not None:
                continue

            termin = Termin(
                naziv=naziv,
                opis=opis,
                datum_vrijeme=now + timedelta(days=day_offset),
                kapacitet=kapacitet,
                created_by_id=admin_id,
            )
            session.add(termin)

        session.commit()

    print("Seed podaci su uspjesno ubaceni.")


if __name__ == "__main__":
    seed_demo_data()
