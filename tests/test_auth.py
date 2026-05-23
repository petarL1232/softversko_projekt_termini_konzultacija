from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def unique_email() -> str:
    """Generira novi email za svaki test da ne dobijemo konflikt u bazi."""

    return f"student-{uuid4()}@example.com"


def test_register_creates_user_without_password_hash() -> None:
    with TestClient(app) as client:
        email = unique_email()

        response = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "test123",
            },
        )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == email
    assert data["role"] == "user"
    assert "id" in data
    assert "password_hash" not in data


def test_register_duplicate_email_returns_409() -> None:
    with TestClient(app) as client:
        email = unique_email()

        first_response = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "test123",
            },
        )

        second_response = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "test123",
            },
        )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_login_with_valid_credentials_returns_token() -> None:
    with TestClient(app) as client:
        email = unique_email()

        client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "test123",
            },
        )

        response = client.post(
            "/auth/login",
            data={
                "username": email,
                "password": "test123",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 20


def test_login_with_wrong_password_returns_401() -> None:
    with TestClient(app) as client:
        email = unique_email()

        client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "test123",
            },
        )

        response = client.post(
            "/auth/login",
            data={
                "username": email,
                "password": "wrong-password",
            },
        )

    assert response.status_code == 401


def test_auth_me_with_valid_token_returns_current_user() -> None:
    with TestClient(app) as client:
        email = unique_email()

        client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "test123",
            },
        )

        login_response = client.post(
            "/auth/login",
            data={
                "username": email,
                "password": "test123",
            },
        )

        token = login_response.json()["access_token"]

        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert me_response.status_code == 200

    data = me_response.json()

    assert data["email"] == email
    assert data["role"] == "user"
    assert "password_hash" not in data


def test_auth_me_without_token_returns_401() -> None:
    with TestClient(app) as client:
        response = client.get("/auth/me")

    assert response.status_code == 401
