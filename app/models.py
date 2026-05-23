from datetime import UTC, datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


class UserRole(StrEnum):
    """Allowed user roles in the system."""

    ADMIN = "admin"
    USER = "user"


class PrijavaStatus(StrEnum):
    """Allowed signup statuses.

    We keep cancelled signups instead of deleting them so the team can later
    show a small audit/history if needed. For capacity calculations, count
    only ACTIVE signups.
    """

    ACTIVE = "active"
    CANCELLED = "cancelled"


class User(SQLModel, table=True):
    """Database table for application users."""

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: UserRole = Field(default=UserRole.USER)


class Termin(SQLModel, table=True):
    """Database table for consultation/lab terms."""

    id: int | None = Field(default=None, primary_key=True)
    naziv: str = Field(min_length=1, index=True)
    opis: str | None = None
    datum_vrijeme: datetime
    kapacitet: int = Field(gt=0)
    created_by_id: int | None = Field(default=None, foreign_key="user.id")


class Prijava(SQLModel, table=True):
    """Database table connecting users and terms."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    termin_id: int = Field(foreign_key="termin.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: PrijavaStatus = Field(default=PrijavaStatus.ACTIVE)


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


class TerminRead(SQLModel):
    id: int
    naziv: str
    opis: str | None
    datum_vrijeme: datetime
    kapacitet: int
    broj_prijava: int = 0
    slobodna_mjesta: int = 0


class PopunjenostResponse(SQLModel):
    termin_id: int
    kapacitet: int
    broj_prijava: int
    slobodna_mjesta: int
    popunjen: bool
