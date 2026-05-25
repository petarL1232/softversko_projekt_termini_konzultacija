from datetime import datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.models import (
    ConsultationTerm,
    Office,
    Subject,
    TermRegistration,
    User,
    UserRole,
)
from app.seed import PROFESSORS, SUBJECTS, seed_mathos_full_data

postgres_only = pytest.mark.skipif(
    engine.dialect.name != "postgresql",
    reason="PostgreSQL trigger/view tests require PostgreSQL.",
)


@pytest.fixture(name="db_session")
def db_session_fixture() -> Session:
    create_db_and_tables()

    with Session(engine) as session:
        clean_database(session)
        yield session
        clean_database(session)


def clean_database(session: Session) -> None:
    session.execute(text("DELETE FROM term_registrations"))
    session.execute(text("DELETE FROM consultation_terms"))
    session.execute(text("DELETE FROM subjects"))
    session.execute(text("DELETE FROM users"))
    session.execute(text("DELETE FROM offices"))
    session.commit()


def create_office(session: Session, capacity: int = 5) -> Office:
    office = Office(office_name="Test office", capacity=capacity)
    session.add(office)
    session.commit()
    session.refresh(office)
    return office


def create_professor(session: Session, office: Office | None = None) -> User:
    if office is None:
        office = create_office(session)

    professor = User(
        first_name="Test",
        last_name="Professor",
        email="prof@test.com",
        password_hash="hash",
        role=UserRole.PROFESSOR,
        office_id=office.office_id,
    )
    session.add(professor)
    session.commit()
    session.refresh(professor)
    return professor


def create_student(session: Session, email: str = "student@test.com") -> User:
    student = User(
        first_name="Student",
        last_name="User",
        email=email,
        password_hash="hash",
        role=UserRole.STUDENT,
    )
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


def create_subject(session: Session) -> Subject:
    subject = Subject(name="Databases", description="Test subject")
    session.add(subject)
    session.commit()
    session.refresh(subject)
    return subject


def create_term(
    session: Session,
    professor: User,
    subject: Subject,
    starts_in_days: int = 7,
) -> ConsultationTerm:
    start_time = datetime.now().replace(microsecond=0) + timedelta(days=starts_in_days)
    term = ConsultationTerm(
        professor_id=professor.user_id,
        subject_id=subject.subject_id,
        start_time=start_time,
        end_time=start_time + timedelta(hours=1),
    )
    session.add(term)
    session.commit()
    session.refresh(term)
    return term


def test_seed_mathos_full_data_creates_initial_database_content(
    db_session: Session,
) -> None:
    seed_mathos_full_data()

    offices = db_session.exec(select(Office)).all()
    professors = db_session.exec(
        select(User).where(User.role == UserRole.PROFESSOR)
    ).all()
    subjects = db_session.exec(select(Subject)).all()
    terms = db_session.exec(select(ConsultationTerm)).all()
    admin = db_session.exec(
        select(User).where(User.email == "admin@example.com")
    ).first()
    student = db_session.exec(
        select(User).where(User.email == "student1@example.com")
    ).first()

    assert len(offices) > 0
    assert len(professors) == len(PROFESSORS)
    assert len(subjects) == len(SUBJECTS)
    assert len(terms) > 0
    assert admin is not None
    assert admin.role == UserRole.ADMIN
    assert student is not None
    assert student.role == UserRole.STUDENT


def test_seed_mathos_full_data_is_idempotent(db_session: Session) -> None:
    seed_mathos_full_data()
    seed_mathos_full_data()

    professors = db_session.exec(
        select(User).where(User.role == UserRole.PROFESSOR)
    ).all()
    subjects = db_session.exec(select(Subject)).all()

    assert len(professors) == len(PROFESSORS)
    assert len(subjects) == len(SUBJECTS)


def test_professor_can_create_consultation_term(db_session: Session) -> None:
    professor = create_professor(db_session)
    subject = create_subject(db_session)

    term = create_term(db_session, professor, subject)

    assert term.term_id is not None


@postgres_only
def test_student_cannot_create_consultation_term(db_session: Session) -> None:
    student = create_student(db_session)
    subject = create_subject(db_session)
    start_time = datetime.now().replace(microsecond=0) + timedelta(days=7)

    invalid_term = ConsultationTerm(
        professor_id=student.user_id,
        subject_id=subject.subject_id,
        start_time=start_time,
        end_time=start_time + timedelta(hours=1),
    )
    db_session.add(invalid_term)

    with pytest.raises(DBAPIError):
        db_session.commit()

    db_session.rollback()


@postgres_only
def test_professor_must_have_office(db_session: Session) -> None:
    professor = User(
        first_name="No",
        last_name="Office",
        email="no.office@test.com",
        password_hash="hash",
        role=UserRole.PROFESSOR,
        office_id=None,
    )
    db_session.add(professor)

    with pytest.raises(DBAPIError):
        db_session.commit()

    db_session.rollback()


@postgres_only
def test_student_cannot_have_office(db_session: Session) -> None:
    office = create_office(db_session)
    student = User(
        first_name="Bad",
        last_name="Student",
        email="bad.student@test.com",
        password_hash="hash",
        role=UserRole.STUDENT,
        office_id=office.office_id,
    )
    db_session.add(student)

    with pytest.raises(DBAPIError):
        db_session.commit()

    db_session.rollback()


@postgres_only
def test_invalid_time_range_is_rejected(db_session: Session) -> None:
    professor = create_professor(db_session)
    subject = create_subject(db_session)
    start_time = datetime.now().replace(microsecond=0) + timedelta(days=7)

    invalid_term = ConsultationTerm(
        professor_id=professor.user_id,
        subject_id=subject.subject_id,
        start_time=start_time,
        end_time=start_time - timedelta(hours=1),
    )
    db_session.add(invalid_term)

    with pytest.raises(DBAPIError):
        db_session.commit()

    db_session.rollback()


@postgres_only
def test_only_students_can_register_for_term(db_session: Session) -> None:
    professor = create_professor(db_session)
    subject = create_subject(db_session)
    term = create_term(db_session, professor, subject)

    registration = TermRegistration(term_id=term.term_id, student_id=professor.user_id)
    db_session.add(registration)

    with pytest.raises(DBAPIError):
        db_session.commit()

    db_session.rollback()


@postgres_only
def test_duplicate_registration_is_rejected(db_session: Session) -> None:
    professor = create_professor(db_session)
    student = create_student(db_session)
    subject = create_subject(db_session)
    term = create_term(db_session, professor, subject)

    db_session.add(TermRegistration(term_id=term.term_id, student_id=student.user_id))
    db_session.commit()

    db_session.add(TermRegistration(term_id=term.term_id, student_id=student.user_id))

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


@postgres_only
def test_office_capacity_is_enforced(db_session: Session) -> None:
    office = create_office(db_session, capacity=1)
    professor = create_professor(db_session, office=office)
    first_student = create_student(db_session, email="first@test.com")
    second_student = create_student(db_session, email="second@test.com")
    subject = create_subject(db_session)
    term = create_term(db_session, professor, subject)

    db_session.add(
        TermRegistration(term_id=term.term_id, student_id=first_student.user_id)
    )
    db_session.commit()

    db_session.add(
        TermRegistration(term_id=term.term_id, student_id=second_student.user_id)
    )

    with pytest.raises(DBAPIError):
        db_session.commit()

    db_session.rollback()


@postgres_only
def test_consultation_overview_view_contains_free_places(db_session: Session) -> None:
    office = create_office(db_session, capacity=3)
    professor = create_professor(db_session, office=office)
    student = create_student(db_session)
    subject = create_subject(db_session)
    term = create_term(db_session, professor, subject)

    db_session.add(TermRegistration(term_id=term.term_id, student_id=student.user_id))
    db_session.commit()

    row = db_session.execute(
        text(
            "SELECT capacity, registered_students, free_places "
            "FROM consultation_overview"
        )
    ).first()

    assert row is not None
    assert row.capacity == 3
    assert row.registered_students == 1
    assert row.free_places == 2
