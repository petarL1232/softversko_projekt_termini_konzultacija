from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.models import User, UserRole
from app.routers.auth import require_admin

VALID_PASSWORD = "StrongPass123!"


def unique_email() -> str:
    """Generira novi email za svaki test da ne dobijemo konflikt u bazi."""

    return f"student-{uuid4()}@example.com"


def register_user(
    client: TestClient,
    email: str,
    password: str = VALID_PASSWORD,
    first_name: str = "Test",
    last_name: str = "Student",
):
    """Helper za register u testovima.

    Namjerno ostaje jednostavan jer auth endpoint testiramo kroz pravi API.
    """

    return client.post(
        "/auth/register",
        json={
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "password": password,
        },
    )


def login_user(
    client: TestClient,
    email: str,
    password: str = VALID_PASSWORD,
):
    """Helper za OAuth2 login formu.

    Backend login ne prima JSON nego form-data:
    username=email, password=lozinka.
    """

    return client.post(
        "/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )


def test_register_creates_user_without_password_hash() -> None:
    with TestClient(app) as client:
        email = unique_email()

        response = register_user(client, email)

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == email
    assert data["role"] == "student"
    assert data["first_name"] == "Test"
    assert data["last_name"] == "Student"
    assert "user_id" in data
    assert "password_hash" not in data


def test_register_duplicate_email_returns_409() -> None:
    with TestClient(app) as client:
        email = unique_email()

        first_response = register_user(client, email)
        second_response = register_user(client, email)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_register_normalizes_email_and_rejects_duplicate_with_spaces() -> None:
    with TestClient(app) as client:
        email = unique_email()
        messy_email = f" {email.upper()} "

        first_response = register_user(client, messy_email)
        second_response = register_user(client, email)

    assert first_response.status_code == 201
    assert first_response.json()["email"] == email
    assert second_response.status_code == 409


def test_register_without_password_returns_422() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json={
                "first_name": "Test",
                "last_name": "Student",
                "email": unique_email(),
            },
        )

    assert response.status_code == 422


def test_register_without_email_returns_422() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json={
                "first_name": "Test",
                "last_name": "Student",
                "password": VALID_PASSWORD,
            },
        )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("password", "expected_message"),
    [
        ("Short1!", "najmanje 12 znakova"),
        ("strongpass123!", "barem jedno veliko slovo"),
        ("STRONGPASS123!", "barem jedno malo slovo"),
        ("StrongPassword!", "barem jedan broj"),
        ("StrongPassword123", "barem jedan specijalni znak"),
    ],
)
def test_register_rejects_weak_passwords(
    password: str,
    expected_message: str,
) -> None:
    with TestClient(app) as client:
        response = register_user(
            client,
            unique_email(),
            password=password,
        )

    assert response.status_code == 400
    assert "Lozinka nije dovoljno jaka" in response.json()["detail"]
    assert expected_message in response.json()["detail"]


@pytest.mark.parametrize(
    "password",
    [
        "Password123!",
        "Qwerty123456!",
        "Admin123456!",
        "Welcome12345!",
        "P@ssw0rd123!",
    ],
)
def test_register_rejects_common_passwords(password: str) -> None:
    with TestClient(app) as client:
        response = register_user(
            client,
            unique_email(),
            password=password,
        )

    assert response.status_code == 400
    assert "cestih lozinki" in response.json()["detail"]


def test_register_accepts_strong_password() -> None:
    with TestClient(app) as client:
        response = register_user(
            client,
            unique_email(),
            password="StrongPass123!",
        )

    assert response.status_code == 201
    assert response.json()["role"] == "student"


def test_login_with_valid_credentials_returns_token() -> None:
    with TestClient(app) as client:
        email = unique_email()

        register_user(client, email)
        response = login_user(client, email)

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 20


def test_login_with_uppercase_email_still_works() -> None:
    with TestClient(app) as client:
        email = unique_email()

        register_user(client, email)
        response = login_user(client, email.upper())

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_with_wrong_password_returns_401() -> None:
    with TestClient(app) as client:
        email = unique_email()

        register_user(client, email)
        response = login_user(client, email, password="wrong-password")

    assert response.status_code == 401


def test_login_with_unknown_email_returns_401() -> None:
    with TestClient(app) as client:
        response = login_user(client, unique_email())

    assert response.status_code == 401


def test_login_with_json_body_returns_422() -> None:
    with TestClient(app) as client:
        email = unique_email()

        register_user(client, email)
        response = client.post(
            "/auth/login",
            json={
                "email": email,
                "password": VALID_PASSWORD,
            },
        )

    assert response.status_code == 422


def test_auth_me_with_valid_token_returns_current_user() -> None:
    with TestClient(app) as client:
        email = unique_email()

        register_user(
            client,
            email,
            first_name="Petar",
            last_name="Tester",
        )
        login_response = login_user(client, email)

        token = login_response.json()["access_token"]

        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert me_response.status_code == 200

    data = me_response.json()

    assert data["email"] == email
    assert data["role"] == "student"
    assert data["first_name"] == "Petar"
    assert data["last_name"] == "Tester"
    assert "user_id" in data
    assert "password_hash" not in data


def test_auth_me_without_token_returns_401() -> None:
    with TestClient(app) as client:
        response = client.get("/auth/me")

    assert response.status_code == 401


def test_auth_me_with_invalid_token_returns_401() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer not-a-real-token"},
        )

    assert response.status_code == 401


def test_auth_me_with_wrong_auth_scheme_returns_401() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Token not-a-bearer-token"},
        )

    assert response.status_code == 401


def test_valid_token_still_works_after_frontend_logout_concept() -> None:
    """Backend JWT ostaje validan dok ne istekne.

    Logout u nasem trenutnom UI-u samo brise token iz localStorage.
    Backend ne vodi blacklistu tokena, pa isti token i dalje vrijedi do isteka.
    """

    with TestClient(app) as client:
        email = unique_email()

        register_user(client, email)
        login_response = login_user(client, email)
        token = login_response.json()["access_token"]

        first_me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        second_me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert first_me_response.status_code == 200
    assert second_me_response.status_code == 200


def test_require_admin_accepts_admin_user() -> None:
    admin_user = User(
        user_id=1,
        first_name="Admin",
        last_name="User",
        email="admin@example.com",
        password_hash="hash",
        role=UserRole.ADMIN,
    )

    result = require_admin(current_user=admin_user)

    assert result is admin_user


def test_require_admin_rejects_student_user() -> None:
    student_user = User(
        user_id=2,
        first_name="Student",
        last_name="User",
        email="student@example.com",
        password_hash="hash",
        role=UserRole.STUDENT,
    )

    with pytest.raises(HTTPException) as exc_info:
        require_admin(current_user=student_user)

    assert exc_info.value.status_code == 403
