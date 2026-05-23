from datetime import UTC, datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


class UserRole(StrEnum):
    """Allowed user roles in the system.

    The original auth flow uses admin/user. The database proposal also mentions
    professor/student, so we keep those values available without breaking auth.
    """

    ADMIN = "admin"
    USER = "user"
    PROFESSOR = "professor"
    STUDENT = "student"


class PrijavaStatus(StrEnum):
    """Allowed signup statuses.

    We keep cancelled signups instead of deleting them so capacity calculations
    can count only active signups and the team can later show history if needed.
    """

    ACTIVE = "active"
    CANCELLED = "cancelled"


class Office(SQLModel, table=True):
    """Office/lab room with a default capacity.

    This keeps the useful part of the database branch, but capacity still also
    exists on Termin because the project MVP says that admin sets capacity for
    each term.
    """

    __tablename__ = "offices"

    id: int | None = Field(default=None, primary_key=True)
    office_name: str = Field(min_length=1, max_length=50, unique=True, index=True)
    capacity: int = Field(gt=0)


class Subject(SQLModel, table=True):
    """Course/subject connected to a consultation or lab term."""

    __tablename__ = "subjects"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(min_length=1, max_length=100, unique=True, index=True)
    description: str | None = None


class User(SQLModel, table=True):
    """Database table for application users.

    Important: auth depends on email, password_hash and role, so those fields
    must stay stable.
    """

    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: UserRole = Field(default=UserRole.USER)

    # Optional fields from the database proposal. They are nullable so existing
    # auth/register still works without asking for first/last name.
    first_name: str | None = None
    last_name: str | None = None
    office_id: int | None = Field(default=None, foreign_key="offices.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Termin(SQLModel, table=True):
    """Database table for consultation/lab terms.

    This is the app's core term model. It keeps the existing Croatian API shape
    while adding optional subject/office links from the database proposal.
    """

    __tablename__ = "consultation_terms"

    id: int | None = Field(default=None, primary_key=True)
    naziv: str = Field(min_length=1, index=True)
    opis: str | None = None
    datum_vrijeme: datetime
    kapacitet: int = Field(gt=0)

    created_by_id: int | None = Field(default=None, foreign_key="users.id")
    subject_id: int | None = Field(default=None, foreign_key="subjects.id")
    office_id: int | None = Field(default=None, foreign_key="offices.id")
    end_time: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Prijava(SQLModel, table=True):
    """Database table connecting users and terms."""

    __tablename__ = "term_registrations"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    termin_id: int = Field(foreign_key="consultation_terms.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: PrijavaStatus = Field(default=PrijavaStatus.ACTIVE)


# Compatibility aliases for teammates who used English domain names while
# prototyping. New code should prefer Termin and Prijava.
ConsultationTerm = Termin
TermRegistration = Prijava


class HealthResponse(SQLModel):
    status: str
    app: str


class RegisterRequest(SQLModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)


class LoginRequest(SQLModel):
    email: str
    password: str


class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(SQLModel):
    id: int
    email: str
    role: UserRole


class TerminCreate(SQLModel):
    naziv: str = Field(min_length=1)
    opis: str | None = None
    datum_vrijeme: datetime
    kapacitet: int = Field(gt=0)
    subject_id: int | None = None
    office_id: int | None = None
    end_time: datetime | None = None


class TerminRead(SQLModel):
    id: int
    naziv: str
    opis: str | None
    datum_vrijeme: datetime
    kapacitet: int
    subject_id: int | None = None
    office_id: int | None = None
    end_time: datetime | None = None
    broj_prijava: int = 0
    slobodna_mjesta: int = 0


class PopunjenostResponse(SQLModel):
    termin_id: int
    kapacitet: int
    broj_prijava: int
    slobodna_mjesta: int
    popunjen: bool
