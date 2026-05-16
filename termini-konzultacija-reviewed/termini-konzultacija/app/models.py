from typing import Optional
from datetime import datetime

from sqlmodel import (
    SQLModel,
    Field
)


class Office(SQLModel, table=True):

    __tablename__ = "offices"

    office_id: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    office_name: str
    capacity: int


class User(SQLModel, table=True):

    __tablename__ = "users"

    user_id: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    first_name: str
    last_name: str

    email: str
    password_hash: str

    role: str

    office_id: Optional[int] = Field(
        default=None,
        foreign_key="offices.office_id"
    )


class Subject(SQLModel, table=True):

    __tablename__ = "subjects"

    subject_id: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    name: str
    description: str


class ConsultationTerm(SQLModel, table=True):

    __tablename__ = "consultation_terms"

    term_id: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    professor_id: int = Field(
        foreign_key="users.user_id"
    )

    subject_id: int = Field(
        foreign_key="subjects.subject_id"
    )

    start_time: datetime
    end_time: datetime


class TermRegistration(SQLModel, table=True):

    __tablename__ = "term_registrations"

    registration_id: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    term_id: int = Field(
        foreign_key="consultation_terms.term_id"
    )

    student_id: int = Field(
        foreign_key="users.user_id"
    )

    registered_at: datetime
