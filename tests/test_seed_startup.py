from sqlmodel import Session, select

from app.database import engine
from app.models import ConsultationTerm, Office, Subject, User, UserRole
from app.seed import DEMO_USERS, PROFESSORS, SUBJECTS, seed_mathos_full_data
from app.services.security import verify_password


def test_seed_mathos_full_data_creates_demo_users() -> None:
    seed_mathos_full_data()

    with Session(engine) as session:
        admin = session.exec(
            select(User).where(User.email == "admin@example.com")
        ).first()
        student1 = session.exec(
            select(User).where(User.email == "student1@example.com")
        ).first()
        student2 = session.exec(
            select(User).where(User.email == "student2@example.com")
        ).first()

    assert admin is not None
    assert admin.role == UserRole.ADMIN
    assert admin.office_id is None
    assert verify_password("admin123", admin.password_hash) is True

    assert student1 is not None
    assert student1.role == UserRole.STUDENT
    assert student1.office_id is None
    assert verify_password("test123", student1.password_hash) is True

    assert student2 is not None
    assert student2.role == UserRole.STUDENT
    assert student2.office_id is None
    assert verify_password("test123", student2.password_hash) is True


def test_seed_mathos_full_data_creates_professors_offices_subjects_and_terms() -> None:
    seed_mathos_full_data()

    with Session(engine) as session:
        offices = session.exec(select(Office)).all()
        professors = session.exec(
            select(User).where(User.role == UserRole.PROFESSOR)
        ).all()
        subjects = session.exec(select(Subject)).all()
        terms = session.exec(select(ConsultationTerm)).all()

    assert len(offices) > 0
    assert len(professors) == len(PROFESSORS)
    assert len(subjects) == len(SUBJECTS)
    assert len(terms) > 0


def test_seed_mathos_full_data_is_idempotent_for_main_counts() -> None:
    seed_mathos_full_data()
    seed_mathos_full_data()

    with Session(engine) as session:
        professors = session.exec(
            select(User).where(User.role == UserRole.PROFESSOR)
        ).all()
        subjects = session.exec(select(Subject)).all()
        demo_users = [
            session.exec(select(User).where(User.email == user_data["email"])).first()
            for user_data in DEMO_USERS
        ]

    assert len(professors) == len(PROFESSORS)
    assert len(subjects) == len(SUBJECTS)
    assert all(user is not None for user in demo_users)


def test_seed_professors_have_offices_and_hashed_passwords() -> None:
    seed_mathos_full_data()

    with Session(engine) as session:
        professors = session.exec(
            select(User).where(User.role == UserRole.PROFESSOR)
        ).all()

    assert professors
    assert all(professor.office_id is not None for professor in professors)
    assert all(
        verify_password("prof123", professor.password_hash) for professor in professors
    )


def test_seed_subject_descriptions_contain_code_semester_and_professors() -> None:
    seed_mathos_full_data()

    with Session(engine) as session:
        subject = session.exec(
            select(Subject).where(Subject.name == SUBJECTS[0]["name"])
        ).first()

    assert subject is not None
    assert SUBJECTS[0]["code"] in subject.description
    assert SUBJECTS[0]["semester"] in subject.description
    assert "Nastavnici:" in subject.description


def test_seed_consultation_terms_have_valid_time_ranges() -> None:
    seed_mathos_full_data()

    with Session(engine) as session:
        terms = session.exec(select(ConsultationTerm)).all()

    assert terms
    assert all(term.end_time > term.start_time for term in terms)


def test_seed_consultation_terms_reference_existing_professors_and_subjects() -> None:
    seed_mathos_full_data()

    with Session(engine) as session:
        terms = session.exec(select(ConsultationTerm)).all()

        for term in terms:
            professor = session.get(User, term.professor_id)
            subject = session.get(Subject, term.subject_id)

            assert professor is not None
            assert professor.role == UserRole.PROFESSOR
            assert subject is not None
