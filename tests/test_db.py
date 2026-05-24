# tests/test_models.py
from datetime import UTC, datetime

from app.models import (
    ConsultationTermCreate,
    ConsultationTermRead,
    HealthResponse,
    OfficeCreate,
    OfficeRead,
    OccupancyResponse,
    RegisterRequest,
    SubjectCreate,
    SubjectRead,
    TermRegistrationRead,
    TerminCreate,
    TokenResponse,
    UserRead,
    UserRole,
    utc_now,
)

# --- UserRole ---

def test_user_role_values() -> None:
    assert UserRole.ADMIN == "admin"
    assert UserRole.PROFESSOR == "professor"
    assert UserRole.STUDENT == "student"


def test_user_role_is_str() -> None:
    assert isinstance(UserRole.ADMIN, str)
    assert isinstance(UserRole.PROFESSOR, str)
    assert isinstance(UserRole.STUDENT, str)


# --- HealthResponse ---

def test_health_response_with_status_only() -> None:
    h = HealthResponse(status="ok")
    assert h.status == "ok"
    assert h.service is None


def test_health_response_with_service() -> None:
    h = HealthResponse(status="ok", service="api")
    assert h.service == "api"


# --- RegisterRequest ---

def test_register_request_defaults() -> None:
    r = RegisterRequest(email="test@example.com", password="secret")
    assert r.first_name == "Student"
    assert r.last_name == "User"
    assert r.email == "test@example.com"
    assert r.password == "secret"


def test_register_request_custom_names() -> None:
    r = RegisterRequest(
        first_name="Ana",
        last_name="Horvat",
        email="ana@example.com",
        password="secret",
    )
    assert r.first_name == "Ana"
    assert r.last_name == "Horvat"


# --- TokenResponse ---

def test_token_response_default_type() -> None:
    t = TokenResponse(access_token="abc123")
    assert t.token_type == "bearer"


def test_token_response_custom_type() -> None:
    t = TokenResponse(access_token="abc123", token_type="jwt")
    assert t.token_type == "jwt"


# --- UserRead ---

def test_user_read_without_office() -> None:
    u = UserRead(
        user_id=1,
        first_name="Ana",
        last_name="Horvat",
        email="ana@example.com",
        role=UserRole.STUDENT,
    )
    assert u.office_id is None
    assert u.role == UserRole.STUDENT


def test_user_read_with_office() -> None:
    u = UserRead(
        user_id=2,
        first_name="Marko",
        last_name="Marić",
        email="marko@example.com",
        role=UserRole.PROFESSOR,
        office_id=5,
    )
    assert u.office_id == 5


# --- OfficeCreate / OfficeRead ---

def test_office_create() -> None:
    o = OfficeCreate(office_name="A101", capacity=10)
    assert o.office_name == "A101"
    assert o.capacity == 10


def test_office_read() -> None:
    o = OfficeRead(office_id=1, office_name="A101", capacity=10)
    assert o.office_id == 1


# --- SubjectCreate / SubjectRead ---

def test_subject_create_without_description() -> None:
    s = SubjectCreate(name="Matematika")
    assert s.description is None


def test_subject_create_with_description() -> None:
    s = SubjectCreate(name="Matematika", description="Linearna algebra")
    assert s.description == "Linearna algebra"


def test_subject_read() -> None:
    s = SubjectRead(subject_id=1, name="Matematika", description=None)
    assert s.subject_id == 1
    assert s.description is None


# --- ConsultationTermCreate / Read ---

def test_consultation_term_create() -> None:
    start = datetime(2025, 6, 1, 10, 0)
    end = datetime(2025, 6, 1, 11, 0)
    t = ConsultationTermCreate(
        professor_id=1,
        subject_id=2,
        start_time=start,
        end_time=end,
    )
    assert t.professor_id == 1
    assert t.start_time < t.end_time


def test_consultation_term_read() -> None:
    now = utc_now()
    t = ConsultationTermRead(
        term_id=1,
        professor_id=1,
        subject_id=2,
        start_time=datetime(2025, 6, 1, 10, 0),
        end_time=datetime(2025, 6, 1, 11, 0),
        created_at=now,
    )
    assert t.term_id == 1
    assert t.created_at == now


# --- TermRegistrationRead ---

def test_term_registration_read() -> None:
    now = utc_now()
    r = TermRegistrationRead(
        registration_id=1,
        term_id=3,
        student_id=7,
        registered_at=now,
    )
    assert r.student_id == 7
    assert r.registered_at == now


# --- OccupancyResponse ---

def test_occupancy_response_not_full() -> None:
    o = OccupancyResponse(
        term_id=1,
        capacity=10,
        registered_students=5,
        free_places=5,
        full=False,
    )
    assert o.free_places == 5
    assert not o.full


def test_occupancy_response_full() -> None:
    o = OccupancyResponse(
        term_id=1,
        capacity=10,
        registered_students=10,
        free_places=0,
        full=True,
    )
    assert o.free_places == 0
    assert o.full


# --- TerminCreate alias ---

def test_termin_create_is_alias_for_consultation_term_create() -> None:
    assert TerminCreate is ConsultationTermCreate