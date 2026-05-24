import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlmodel import Session, select

from app.database import engine
from app.models import (
    ConsultationTerm,
    Office,
    Subject,
    TermRegistration,
    User,
    UserRole,
)


def clean_database(session: Session) -> None:
    session.execute(text("DELETE FROM term_registrations"))
    session.execute(text("DELETE FROM consultation_terms"))
    session.execute(text("DELETE FROM subjects"))
    session.execute(text("DELETE FROM users"))
    session.execute(text("DELETE FROM offices"))
    session.commit()


@pytest.fixture
def session():
    with Session(engine) as session:
        clean_database(session)
        yield session
        session.rollback()


def create_professor(session: Session) -> User:
    office = Office(
        office_name="Test office",
        capacity=5,
    )

    session.add(office)
    session.commit()
    session.refresh(office)

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


def create_student(session: Session) -> User:
    student = User(
        first_name="Student",
        last_name="User",
        email="student@test.com",
        password_hash="hash",
        role=UserRole.STUDENT,
    )

    session.add(student)
    session.commit()
    session.refresh(student)

    return student


def create_subject(session: Session) -> Subject:
    subject = Subject(
        name="Databases",
        description="Test subject",
    )

    session.add(subject)
    session.commit()
    session.refresh(subject)

    return subject


def create_term(
    session: Session,
    professor: User,
    subject: Subject,
) -> ConsultationTerm:
    from datetime import datetime, timedelta

    term = ConsultationTerm(
        professor_id=professor.user_id,
        subject_id=subject.subject_id,
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=1),
    )

    session.add(term)
    session.commit()
    session.refresh(term)

    return term


def test_professor_consultation_creation(session: Session):
    professor = create_professor(session)
    subject = create_subject(session)

    term = create_term(session, professor, subject)

    assert term.term_id is not None


def test_student_cannot_create_consultation(session: Session):
    student = create_student(session)
    subject = create_subject(session)

    from datetime import datetime, timedelta

    invalid_term = ConsultationTerm(
        professor_id=student.user_id,
        subject_id=subject.subject_id,
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=1),
    )

    session.add(invalid_term)

    with pytest.raises(DBAPIError):
        session.commit()

    session.rollback()


def test_duplicate_registration_trigger(session: Session):
    professor = create_professor(session)
    student = create_student(session)
    subject = create_subject(session)

    term = create_term(session, professor, subject)

    registration = TermRegistration(
        term_id=term.term_id,
        student_id=student.user_id,
    )

    session.add(registration)
    session.commit()

    duplicate = TermRegistration(
        term_id=term.term_id,
        student_id=student.user_id,
    )

    session.add(duplicate)

    with pytest.raises(DBAPIError):
        session.commit()

    session.rollback()


def test_invalid_time_range(session: Session):
    professor = create_professor(session)
    subject = create_subject(session)

    from datetime import datetime, timedelta

    invalid_term = ConsultationTerm(
        professor_id=professor.user_id,
        subject_id=subject.subject_id,
        start_time=datetime.now(),
        end_time=datetime.now() - timedelta(hours=1),
    )

    session.add(invalid_term)

    with pytest.raises(DBAPIError):
        session.commit()

    session.rollback()
