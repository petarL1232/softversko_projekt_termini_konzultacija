from datetime import UTC, datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


class HealthResponse(SQLModel):
    status: str
    service: str | None = None


def utc_now() -> datetime:
    """Return a timezone-neutral UTC timestamp for database fields."""

    return datetime.now(UTC).replace(tzinfo=None)


class UserRole(StrEnum):
    """Application roles stored in the users.role column."""

    ADMIN = "admin"
    PROFESSOR = "professor"
    STUDENT = "student"


class Office(SQLModel, table=True):
    __tablename__ = "offices"

    office_id: int | None = Field(default=None, primary_key=True)
    office_name: str = Field(index=True, unique=True, max_length=50)
    capacity: int = Field(gt=0)


class User(SQLModel, table=True):
    __tablename__ = "users"

    user_id: int | None = Field(default=None, primary_key=True)
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    email: str = Field(index=True, unique=True, max_length=100)
    password_hash: str
    role: UserRole = Field(default=UserRole.STUDENT)
    office_id: int | None = Field(default=None, foreign_key="offices.office_id")
    created_at: datetime = Field(default_factory=utc_now)


class Subject(SQLModel, table=True):
    __tablename__ = "subjects"

    subject_id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=100)
    description: str | None = None


class ConsultationTerm(SQLModel, table=True):
    __tablename__ = "consultation_terms"

    term_id: int | None = Field(default=None, primary_key=True)
    professor_id: int = Field(foreign_key="users.user_id")
    subject_id: int = Field(foreign_key="subjects.subject_id")
    start_time: datetime
    end_time: datetime
    created_at: datetime = Field(default_factory=utc_now)


class TermRegistration(SQLModel, table=True):
    __tablename__ = "term_registrations"

    registration_id: int | None = Field(default=None, primary_key=True)
    term_id: int = Field(foreign_key="consultation_terms.term_id")
    student_id: int = Field(foreign_key="users.user_id")
    registered_at: datetime = Field(default_factory=utc_now)


# Request/response schemas for auth.


class RegisterRequest(SQLModel):
    first_name: str = "Student"
    last_name: str = "User"
    email: str
    password: str


class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(SQLModel):
    user_id: int
    first_name: str
    last_name: str
    email: str
    role: UserRole
    office_id: int | None = None


class UserRoleUpdateRequest(SQLModel):
    role: UserRole
    office_id: int | None = None


# Request/response schemas for future consultation term endpoints.


class OfficeCreate(SQLModel):
    office_name: str
    capacity: int = Field(gt=0)


class OfficeRead(SQLModel):
    office_id: int
    office_name: str
    capacity: int


class SubjectCreate(SQLModel):
    name: str
    description: str | None = None


class SubjectRead(SQLModel):
    subject_id: int
    name: str
    description: str | None = None


class ConsultationTermCreate(SQLModel):
    professor_id: int
    subject_id: int
    start_time: datetime
    end_time: datetime


class ConsultationTermRead(SQLModel):
    term_id: int
    professor_id: int
    subject_id: int
    start_time: datetime
    end_time: datetime
    created_at: datetime


class TermRegistrationRead(SQLModel):
    registration_id: int
    term_id: int
    student_id: int
    registered_at: datetime


class OccupancyResponse(SQLModel):
    term_id: int
    capacity: int
    registered_students: int
    free_places: int
    full: bool


# Temporary compatibility alias while old router skeleton is being renamed.
# TODO: when termini.py is fully migrated, import ConsultationTermCreate directly.
TerminCreate = ConsultationTermCreate
