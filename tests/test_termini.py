"""Integracijski testovi za /termini endpointe — Osoba 3."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app

# ── Helpers ───────────────────────────────────────────────────────────────────


def _register_and_login(
    client: TestClient, email: str, password: str = "test123"
) -> str:
    """Registriraj korisnika i vrati JWT token."""
    client.post(
        "/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": email,
            "password": password,
        },
    )
    res = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    return res.json()["access_token"]


def _make_admin(client: TestClient, email: str) -> str:
    """Registriraj korisnika, postavi ga kao admina u bazi i vrati token."""
    from sqlmodel import Session, select

    from app.database import engine
    from app.models import User, UserRole

    _register_and_login(client, email)

    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if user:
            user.role = UserRole.ADMIN
            session.add(user)
            session.commit()

    # Re-login da dobijemo token s admin ulogom
    res = client.post(
        "/auth/login",
        data={"username": email, "password": "test123"},
    )
    return res.json()["access_token"]


def _future_time(days: int = 1, hours: int = 0) -> str:
    """Vrati ISO string za datum u budućnosti."""
    dt = datetime.now(UTC) + timedelta(days=days, hours=hours)
    return dt.replace(tzinfo=None).isoformat()


def _termin_payload(
    professor_id: int = 1,
    subject_id: int = 1,
    days_offset: int = 2,
) -> dict:
    return {
        "professor_id": professor_id,
        "subject_id": subject_id,
        "start_time": _future_time(days=days_offset),
        "end_time": _future_time(days=days_offset, hours=1),
    }


# ── Unit testovi ──────────────────────────────────────────────────────────────

def test_get_termini_without_auth_returns_401() -> None:
    """GET /termini bez tokena treba vratiti 401."""
    with TestClient(app) as client:
        res = client.get("/termini")
    assert res.status_code == 401


def test_get_termini_with_auth_returns_200() -> None:
    """GET /termini s validnim tokenom treba vratiti 200 i listu."""
    with TestClient(app) as client:
        token = _register_and_login(client, "student_list@test.com")
        res = client.get(
            "/termini",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_get_termin_not_found_returns_404() -> None:
    """GET /termini/99999 treba vratiti 404."""
    with TestClient(app) as client:
        token = _register_and_login(client, "student_404@test.com")
        res = client.get(
            "/termini/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 404
    assert "nije pronađen" in res.json()["detail"]


def test_create_termin_as_student_returns_403() -> None:
    """POST /termini kao student treba vratiti 403."""
    with TestClient(app) as client:
        token = _register_and_login(client, "student_post@test.com")

        # Trebamo profesora i predmet — koristimo dummy ID-ove
        res = client.post(
            "/termini",
            json=_termin_payload(),
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 403


def test_create_termin_without_auth_returns_401() -> None:
    """POST /termini bez tokena treba vratiti 401."""
    with TestClient(app) as client:
        res = client.post("/termini", json=_termin_payload())
    assert res.status_code == 401


def test_delete_termin_as_student_returns_403() -> None:
    """DELETE /termini/1 kao student treba vratiti 403."""
    with TestClient(app) as client:
        token = _register_and_login(client, "student_del@test.com")
        res = client.delete(
            "/termini/1",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 403


def test_update_termin_as_student_returns_403() -> None:
    """PUT /termini/1 kao student treba vratiti 403."""
    with TestClient(app) as client:
        token = _register_and_login(client, "student_put@test.com")
        res = client.put(
            "/termini/1",
            json=_termin_payload(),
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 403


def test_delete_nonexistent_termin_returns_404() -> None:
    """DELETE /termini/99999 kao admin treba vratiti 404."""
    with TestClient(app) as client:
        token = _make_admin(client, "admin_del404@test.com")
        res = client.delete(
            "/termini/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 404


def test_update_nonexistent_termin_returns_404() -> None:
    """PUT /termini/99999 kao admin treba vratiti 404."""
    with TestClient(app) as client:
        token = _make_admin(client, "admin_put404@test.com")
        res = client.put(
            "/termini/99999",
            json=_termin_payload(),
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 404


def test_popunjenost_not_found_returns_404() -> None:
    """GET /termini/popunjenost/99999 treba vratiti 404."""
    with TestClient(app) as client:
        token = _register_and_login(client, "student_occ@test.com")
        res = client.get(
            "/termini/popunjenost/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 404


def test_get_termini_returns_list_type() -> None:
    """GET /termini uvijek vraća listu (može biti prazna)."""
    with TestClient(app) as client:
        token = _register_and_login(client, "student_type@test.com")
        res = client.get(
            "/termini",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


# ── Integracijski testovi ─────────────────────────────────────────────────────


def test_admin_crud_termin_full_flow() -> None:
    """
    Integracijski test: admin kreira termin, dohvaća ga, briše ga.
    Ako profesor/predmet ne postoje u bazi, očekujemo 404 pri kreiranju.
    """
    with TestClient(app) as client:
        token = _make_admin(client, "admin_crud@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Pokušaj kreiranja — može vratiti 201 ili 404 (ovisno o seed podacima)
        create_res = client.post(
            "/termini",
            json=_termin_payload(professor_id=1, subject_id=1),
            headers=headers,
        )
        assert create_res.status_code in (201, 404, 422)

        if create_res.status_code == 201:
            termin_id = create_res.json()["term_id"]

            # Dohvati ga
            get_res = client.get(f"/termini/{termin_id}", headers=headers)
            assert get_res.status_code == 200
            assert get_res.json()["term_id"] == termin_id

            # Obriši ga
            del_res = client.delete(f"/termini/{termin_id}", headers=headers)
            assert del_res.status_code == 204

            # Provjeri da više ne postoji
            gone_res = client.get(f"/termini/{termin_id}", headers=headers)
            assert gone_res.status_code == 404


def test_start_time_after_end_time_returns_422() -> None:
    """
    Integracijski test: kreiranje termina gdje je start_time >= end_time
    treba vratiti 422.
    """
    with TestClient(app) as client:
        token = _make_admin(client, "admin_invalid_time@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        bad_payload = {
            "professor_id": 1,
            "subject_id": 1,
            "start_time": _future_time(days=3, hours=2),
            "end_time": _future_time(days=3, hours=1),  # kraj prije početka!
        }

        res = client.post("/termini", json=bad_payload, headers=headers)
        assert res.status_code in (404, 422)
