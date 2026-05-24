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
from app.models import ConsultationTerm, Office, Subject, User, UserRole
from app.services.security import hash_password

DEMO_USERS = [
    ("admin@example.com", "admin123", UserRole.ADMIN),
    ("student1@example.com", "test123", UserRole.STUDENT),
    ("student2@example.com", "test123", UserRole.STUDENT),
    ("student3@example.com", "test123", UserRole.STUDENT),
]

DEMO_SUBJECTS = [
    ("Matematika", "Osnovni predmet"),
    ("Programiranje", "Predmet za razvoj softvera"),
    ("Baze podataka", "SQL i upravljanje bazama"),
]

DEMO_TERMINI = [
    (1, 1, 1, "09:00"),  # subject_id, professor_id, day_offset, time
    (2, 1, 2, "10:00"),
    (3, 1, 3, "14:00"),
]


def seed_demo_data() -> None:
    """Insert demo users and terms if they do not already exist."""

    create_db_and_tables()

    with Session(engine) as session:
        admin_id: int | None = None
        admin_user: User | None = None

        # Create users
        for email, password, role in DEMO_USERS:
            existing_user = session.exec(
                select(User).where(User.email == email)
            ).first()
            if existing_user is None:
                user = User(
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                    first_name=email.split("@")[0],
                    last_name="User",
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                existing_user = user

            if role == UserRole.ADMIN:
                admin_id = existing_user.user_id
                admin_user = existing_user

        if admin_id is None or admin_user is None:
            raise RuntimeError("Admin korisnik nije kreiran.")

        # Create office for admin if not exists
        if admin_user.office_id is None:
            existing_office = session.exec(
                select(Office).where(Office.office_name == "Office 1")
            ).first()
            if existing_office is None:
                office = Office(office_name="Office 1", capacity=5)
                session.add(office)
                session.commit()
                session.refresh(office)
                existing_office = office
            
            admin_user.office_id = existing_office.office_id
            session.add(admin_user)
            session.commit()

        # Create subjects
        for subject_name, description in DEMO_SUBJECTS:
            existing_subject = session.exec(
                select(Subject).where(Subject.name == subject_name)
            ).first()
            if existing_subject is None:
                subject = Subject(name=subject_name, description=description)
                session.add(subject)

        session.commit()

        # Create consultation terms
        now = datetime.now(UTC)

        for subject_id, professor_id, day_offset, time_str in DEMO_TERMINI:
            hour, minute = map(int, time_str.split(":"))
            start_time = now + timedelta(days=day_offset)
            start_time = start_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            end_time = start_time + timedelta(hours=1)

            existing_termin = session.exec(
                select(ConsultationTerm).where(
                    ConsultationTerm.professor_id == professor_id,
                    ConsultationTerm.subject_id == subject_id,
                    ConsultationTerm.start_time == start_time,
                )
            ).first()
            if existing_termin is not None:
                continue

            termin = ConsultationTerm(
                professor_id=professor_id,
                subject_id=subject_id,
                start_time=start_time,
                end_time=end_time,
            )
            session.add(termin)

        session.commit()

    print("Seed podaci su uspjesno ubaceni.")


if __name__ == "__main__":
    seed_demo_data()

