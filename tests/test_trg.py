from sqlalchemy import text
from sqlmodel import Session

from app.database import create_db_and_tables, engine
from app.models import (
    ConsultationTerm,
    Office,
    Subject,
    TermRegistration,
    User,
    UserRole,
)


def print_result(name: str, success: bool, error: str | None = None) -> None:
    if success:
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name}")
        if error:
            print(f"       {error}")


def reset_database(session: Session) -> None:
    session.exec(text("DELETE FROM term_registrations"))
    session.exec(text("DELETE FROM consultation_terms"))
    session.exec(text("DELETE FROM subjects"))
    session.exec(text("DELETE FROM users"))
    session.exec(text("DELETE FROM offices"))

    session.commit()


def create_test_data(session: Session) -> tuple[User, User, Subject]:
    office = Office(
        office_name="Test Office",
        capacity=5,
    )

    session.add(office)
    session.commit()
    session.refresh(office)

    professor = User(
        first_name="Profesor",
        last_name="Test",
        email="prof@test.com",
        password_hash="12345678",
        role=UserRole.PROFESSOR,
        office_id=office.office_id,
    )

    student = User(
        first_name="Student",
        last_name="Test",
        email="student@test.com",
        password_hash="12345678",
        role=UserRole.STUDENT,
    )

    subject = Subject(
        name="Test Subject",
        description="Test Description",
    )

    session.add(professor)
    session.add(student)
    session.add(subject)

    session.commit()

    session.refresh(professor)
    session.refresh(student)
    session.refresh(subject)

    return professor, student, subject


def test_professor_consultation_creation(session: Session) -> ConsultationTerm:
    professor, _, subject = create_test_data(session)

    term = ConsultationTerm(
        professor_id=professor.user_id,
        subject_id=subject.subject_id,
        start_time="2026-06-01 09:00:00",
        end_time="2026-06-01 10:00:00",
    )

    session.add(term)
    session.commit()
    session.refresh(term)

    print_result(
        "Professor can create consultation term",
        True,
    )

    return term


def test_student_cannot_create_consultation(session: Session) -> None:
    _, student, subject = create_test_data(session)

    try:
        invalid_term = ConsultationTerm(
            professor_id=student.user_id,
            subject_id=subject.subject_id,
            start_time="2026-06-02 09:00:00",
            end_time="2026-06-02 10:00:00",
        )

        session.add(invalid_term)
        session.commit()

        print_result(
            "Student cannot create consultation term",
            False,
            "Trigger did not stop invalid insert",
        )

    except Exception as error:
        session.rollback()

        print_result(
            "Student cannot create consultation term",
            True,
            str(error),
        )


def test_duplicate_registration_trigger(session: Session) -> None:
    professor, student, subject = create_test_data(session)

    term = ConsultationTerm(
        professor_id=professor.user_id,
        subject_id=subject.subject_id,
        start_time="2026-06-03 09:00:00",
        end_time="2026-06-03 10:00:00",
    )

    session.add(term)
    session.commit()
    session.refresh(term)

    registration = TermRegistration(
        term_id=term.term_id,
        student_id=student.user_id,
    )

    session.add(registration)
    session.commit()

    try:
        duplicate_registration = TermRegistration(
            term_id=term.term_id,
            student_id=student.user_id,
        )

        session.add(duplicate_registration)
        session.commit()

        print_result(
            "Duplicate registration prevention",
            False,
            "Duplicate registration was allowed",
        )

    except Exception as error:
        session.rollback()

        print_result(
            "Duplicate registration prevention",
            True,
            str(error),
        )


def test_invalid_time_range(session: Session) -> None:
    professor, _, subject = create_test_data(session)

    try:
        invalid_term = ConsultationTerm(
            professor_id=professor.user_id,
            subject_id=subject.subject_id,
            start_time="2026-06-04 11:00:00",
            end_time="2026-06-04 10:00:00",
        )

        session.add(invalid_term)
        session.commit()

        print_result(
            "Invalid time range prevention",
            False,
            "Invalid time range was allowed",
        )

    except Exception as error:
        session.rollback()

        print_result(
            "Invalid time range prevention",
            True,
            str(error),
        )


def main() -> None:
    create_db_and_tables()

    with Session(engine) as session:
        reset_database(session)

        print("\n=== RUNNING DATABASE TESTS ===\n")

        test_professor_consultation_creation(session)

        reset_database(session)

        test_student_cannot_create_consultation(session)

        reset_database(session)

        test_duplicate_registration_trigger(session)

        reset_database(session)

        test_invalid_time_range(session)

        print("\n=== TESTS FINISHED ===\n")


if __name__ == "__main__":
    main()
