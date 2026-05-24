# Osoba 4 – Testovi za prijave / odjave s konzultacijskih termina
"""
Testovi pokrivaju sve endpointe iz app/routers/prijave.py:
  POST /termini/{termin_id}/prijava   – prijava studenta na termin
  DELETE /termini/{termin_id}/prijava – odjava studenta s termina
  GET /me/prijave                     – pregled vlastitih prijava
  GET /termini/{termin_id}/popunjenost – popunjenost termina

Testovi koriste SQLite bazu u memoriji (ne treba PostgreSQL ni Docker).
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, StaticPool, create_engine

# Postavi SQLite PRIJE importa app modula da engine ne pokuša spajanje na Postgres
os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.main import app  # noqa: E402
from app.database import get_session  # noqa: E402
from app.models import (  # noqa: E402
    ConsultationTerm,
    Office,
    Subject,
    User,
    UserRole,
)
from app.services.security import hash_password  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SQLITE_URL = "sqlite://"  # in-memory


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Pomoćne funkcije za postavljanje podataka
# ---------------------------------------------------------------------------


def _create_office(session: Session, name: str = "A101", capacity: int = 5) -> Office:
    office = Office(office_name=name, capacity=capacity)
    session.add(office)
    session.commit()
    session.refresh(office)
    return office


def _create_professor(
    session: Session, email: str = "prof@fesb.hr", office_id: int | None = None
) -> User:
    user = User(
        first_name="Profesor",
        last_name="Testić",
        email=email,
        password_hash=hash_password("prof123"),
        role=UserRole.ADMIN,
        office_id=office_id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _create_student(session: Session, email: str = "student@fesb.hr") -> User:
    user = User(
        first_name="Student",
        last_name="Testić",
        email=email,
        password_hash=hash_password("student123"),
        role=UserRole.STUDENT,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _create_subject(session: Session, name: str = "Matematika") -> Subject:
    subject = Subject(name=name, description="Opis predmeta")
    session.add(subject)
    session.commit()
    session.refresh(subject)
    return subject


def _create_term(
    session: Session,
    professor_id: int,
    subject_id: int,
    start: str = "2030-01-10T09:00:00",
    end: str = "2030-01-10T10:00:00",
) -> ConsultationTerm:
    from datetime import datetime

    term = ConsultationTerm(
        professor_id=professor_id,
        subject_id=subject_id,
        start_time=datetime.fromisoformat(start),
        end_time=datetime.fromisoformat(end),
    )
    session.add(term)
    session.commit()
    session.refresh(term)
    return term


def _login(client: TestClient, email: str, password: str) -> str:
    """Vrati Bearer token za korisnika."""
    response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Testovi: POST /termini/{termin_id}/prijava
# ---------------------------------------------------------------------------


class TestPrijaviSeNaTermin:
    """Testovi za prijavu studenta na konzultacijski termin."""

    def test_uspjesna_prijava(self, client: TestClient, session: Session):
        office = _create_office(session)
        professor = _create_professor(session, office_id=office.office_id)
        student = _create_student(session)
        subject = _create_subject(session)
        term = _create_term(session, professor.user_id, subject.subject_id)

        token = _login(client, student.email, "student123")
        response = client.post(
            f"/termini/{term.term_id}/prijava",
            headers=_auth_headers(token),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["term_id"] == term.term_id
        assert data["student_id"] == student.user_id
        assert "registration_id" in data
        assert "registered_at" in data

    def test_prijava_nepostojeci_termin_vraca_404(
        self, client: TestClient, session: Session
    ):
        student = _create_student(session)
        token = _login(client, student.email, "student123")

        response = client.post(
            "/termini/9999/prijava",
            headers=_auth_headers(token),
        )

        assert response.status_code == 404

    def test_dvostruka_prijava_vraca_409(self, client: TestClient, session: Session):
        office = _create_office(session)
        professor = _create_professor(session, office_id=office.office_id)
        student = _create_student(session)
        subject = _create_subject(session)
        term = _create_term(session, professor.user_id, subject.subject_id)

        token = _login(client, student.email, "student123")
        headers = _auth_headers(token)

        first = client.post(f"/termini/{term.term_id}/prijava", headers=headers)
        second = client.post(f"/termini/{term.term_id}/prijava", headers=headers)

        assert first.status_code == 201
        assert second.status_code == 409
        assert "već prijavljen" in second.json()["detail"]

    def test_prijava_popunjenog_termina_vraca_409(
        self, client: TestClient, session: Session
    ):
        # Kapacitet ureda = 1, zatim dva studenta pokušavaju se prijaviti
        office = _create_office(session, capacity=1)
        professor = _create_professor(session, office_id=office.office_id)
        subject = _create_subject(session)
        term = _create_term(session, professor.user_id, subject.subject_id)

        student1 = _create_student(session, email="s1@test.hr")
        student2 = _create_student(session, email="s2@test.hr")

        token1 = _login(client, student1.email, "student123")
        token2 = _login(client, student2.email, "student123")

        first = client.post(
            f"/termini/{term.term_id}/prijava", headers=_auth_headers(token1)
        )
        second = client.post(
            f"/termini/{term.term_id}/prijava", headers=_auth_headers(token2)
        )

        assert first.status_code == 201
        assert second.status_code == 409
        assert "popunjen" in second.json()["detail"].lower()

    def test_prijava_bez_tokena_vraca_401(self, client: TestClient, session: Session):
        office = _create_office(session)
        professor = _create_professor(session, office_id=office.office_id)
        subject = _create_subject(session)
        term = _create_term(session, professor.user_id, subject.subject_id)

        response = client.post(f"/termini/{term.term_id}/prijava")
        assert response.status_code == 401

    def test_prijava_termin_bez_kapaciteta_vraca_409(
        self, client: TestClient, session: Session
    ):
        """Termin čiji profesor nema ured – kapacitet 0."""
        professor = _create_professor(session, office_id=None)
        student = _create_student(session)
        subject = _create_subject(session)
        term = _create_term(session, professor.user_id, subject.subject_id)

        token = _login(client, student.email, "student123")
        response = client.post(
            f"/termini/{term.term_id}/prijava",
            headers=_auth_headers(token),
        )

        assert response.status_code == 409


# ---------------------------------------------------------------------------
# Testovi: DELETE /termini/{termin_id}/prijava
# ---------------------------------------------------------------------------


class TestOdjaviSeSTermin:
    """Testovi za odjavu studenta s konzultacijskog termina."""

    def test_uspjesna_odjava(self, client: TestClient, session: Session):
        office = _create_office(session)
        professor = _create_professor(session, office_id=office.office_id)
        student = _create_student(session)
        subject = _create_subject(session)
        term = _create_term(session, professor.user_id, subject.subject_id)

        token = _login(client, student.email, "student123")
        headers = _auth_headers(token)

        client.post(f"/termini/{term.term_id}/prijava", headers=headers)
        response = client.delete(f"/termini/{term.term_id}/prijava", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["termin_id"] == term.term_id
        assert "Odjava uspješna" in data["message"]

    def test_odjava_neprijavljen_student_vraca_404(
        self, client: TestClient, session: Session
    ):
        office = _create_office(session)
        professor = _create_professor(session, office_id=office.office_id)
        student = _create_student(session)
        subject = _create_subject(session)
        term = _create_term(session, professor.user_id, subject.subject_id)

        token = _login(client, student.email, "student123")
        response = client.delete(
            f"/termini/{term.term_id}/prijava",
            headers=_auth_headers(token),
        )

        assert response.status_code == 404
        assert "nije prijavljen" in response.json()["detail"]

    def test_odjava_nepostojeci_termin_vraca_404(
        self, client: TestClient, session: Session
    ):
        student = _create_student(session)
        token = _login(client, student.email, "student123")

        response = client.delete(
            "/termini/9999/prijava",
            headers=_auth_headers(token),
        )

        assert response.status_code == 404

    def test_odjava_bez_tokena_vraca_401(self, client: TestClient, session: Session):
        office = _create_office(session)
        professor = _create_professor(session, office_id=office.office_id)
        subject = _create_subject(session)
        term = _create_term(session, professor.user_id, subject.subject_id)

        response = client.delete(f"/termini/{term.term_id}/prijava")
        assert response.status_code == 401

    def test_nakon_odjave_moze_se_opet_prijaviti(
        self, client: TestClient, session: Session
    ):
        """Student se može ponovo prijaviti na isti termin nakon odjave."""
        office = _create_office(session)
        professor = _create_professor(session, office_id=office.office_id)
        student = _create_student(session)
        subject = _create_subject(session)
        term = _create_term(session, professor.user_id, subject.subject_id)

        token = _login(client, student.email, "student123")
        headers = _auth_headers(token)

        client.post(f"/termini/{term.term_id}/prijava", headers=headers)
        client.delete(f"/termini/{term.term_id}/prijava", headers=headers)
        ponovna = client.post(f"/termini/{term.term_id}/prijava", headers=headers)

        assert ponovna.status_code == 201

    def test_odjava_jednog_studenta_ne_utjece_na_drugog(
        self, client: TestClient, session: Session
    ):
        office = _create_office(session, capacity=3)
        professor = _create_professor(session, office_id=office.office_id)
        subject = _create_subject(session)
        term = _create_term(session, professor.user_id, subject.subject_id)

        student1 = _create_student(session, email="s1@test.hr")
        student2 = _create_student(session, email="s2@test.hr")

        tok1 = _login(client, student1.email, "student123")
        tok2 = _login(client, student2.email, "student123")

        client.post(f"/termini/{term.term_id}/prijava", headers=_auth_headers(tok1))
        client.post(f"/termini/{term.term_id}/prijava", headers=_auth_headers(tok2))

        client.delete(f"/termini/{term.term_id}/prijava", headers=_auth_headers(tok1))

        # Student 2 je i dalje prijavljen – dvostruka odjava za njega je 404
        still_ok = client.delete(
            f"/termini/{term.term_id}/prijava", headers=_auth_headers(tok1)
        )
        assert still_ok.status_code == 404

        # Student 2 može se odjaviti normalno
        odjava2 = client.delete(
            f"/termini/{term.term_id}/prijava", headers=_auth_headers(tok2)
        )
        assert odjava2.status_code == 200


# ---------------------------------------------------------------------------
# Testovi: GET /me/prijave
# ---------------------------------------------------------------------------


class TestMojePrijave:
    """Testovi za dohvat vlastitih prijava studenta."""

    def test_prazna_lista_za_novog_korisnika(
        self, client: TestClient, session: Session
    ):
        student = _create_student(session)
        token = _login(client, student.email, "student123")

        response = client.get("/me/prijave", headers=_auth_headers(token))

        assert response.status_code == 200
        assert response.json() == []

    def test_vraca_prijavljene_termine(self, client: TestClient, session: Session):
        office = _create_office(session, capacity=10)
        professor = _create_professor(session, office_id=office.office_id)
        student = _create_student(session)
        subject = _create_subject(session)

        term1 = _create_term(
            session,
            professor.user_id,
            subject.subject_id,
            start="2030-02-01T09:00:00",
            end="2030-02-01T10:00:00",
        )
        term2 = _create_term(
            session,
            professor.user_id,
            subject.subject_id,
            start="2030-02-02T09:00:00",
            end="2030-02-02T10:00:00",
        )

        token = _login(client, student.email, "student123")
        headers = _auth_headers(token)

        client.post(f"/termini/{term1.term_id}/prijava", headers=headers)
        client.post(f"/termini/{term2.term_id}/prijava", headers=headers)

        response = client.get("/me/prijave", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        term_ids = [item["termin"]["term_id"] for item in data]
        assert term1.term_id in term_ids
        assert term2.term_id in term_ids

    def test_student_vidi_samo_svoje_prijave(
        self, client: TestClient, session: Session
    ):
        office = _create_office(session, capacity=10)
        professor = _create_professor(session, office_id=office.office_id)
        subject = _create_subject(session)
        term = _create_term(session, professor.user_id, subject.subject_id)

        student1 = _create_student(session, email="s1@test.hr")
        student2 = _create_student(session, email="s2@test.hr")

        tok1 = _login(client, student1.email, "student123")
        tok2 = _login(client, student2.email, "student123")

        client.post(f"/termini/{term.term_id}/prijava", headers=_auth_headers(tok1))

        resp1 = client.get("/me/prijave", headers=_auth_headers(tok1))
        resp2 = client.get("/me/prijave", headers=_auth_headers(tok2))

        assert len(resp1.json()) == 1
        assert len(resp2.json()) == 0

    def test_bez_tokena_vraca_401(self, client: TestClient, session: Session):
        response = client.get("/me/prijave")
        assert response.status_code == 401

    def test_struktura_odgovora_sadrzi_detalje_termina(
        self, client: TestClient, session: Session
    ):
        office = _create_office(session, capacity=5)
        professor = _create_professor(session, office_id=office.office_id)
        student = _create_student(session)
        subject = _create_subject(session)
        term = _create_term(session, professor.user_id, subject.subject_id)

        token = _login(client, student.email, "student123")
        headers = _auth_headers(token)
        client.post(f"/termini/{term.term_id}/prijava", headers=headers)

        response = client.get("/me/prijave", headers=headers)
        data = response.json()

        assert len(data) == 1
        item = data[0]
        assert "registration_id" in item
        assert "registered_at" in item
        assert "termin" in item
        termin = item["termin"]
        assert "term_id" in termin
        assert "professor_id" in termin
        assert "subject_id" in termin
        assert "start_time" in termin
        assert "end_time" in termin


# ---------------------------------------------------------------------------
# Testovi: GET /termini/{termin_id}/popunjenost
# ---------------------------------------------------------------------------


class TestPopunjenostTermina:
    """Testovi za endpoint popunjenosti termina."""

    def test_prazan_termin(self, client: TestClient, session: Session):
        office = _create_office(session, capacity=5)
        professor = _create_professor(session, office_id=office.office_id)
        subject = _create_subject(session)
        term = _create_term(session, professor.user_id, subject.subject_id)

        student = _create_student(session)
        token = _login(client, student.email, "student123")

        response = client.get(
            f"/termini/{term.term_id}/popunjenost",
            headers=_auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["capacity"] == 5
        assert data["registered_students"] == 0
        assert data["free_places"] == 5
        assert data["full"] is False

    def test_djelomicno_popunjen_termin(self, client: TestClient, session: Session):
        office = _create_office(session, capacity=3)
        professor = _create_professor(session, office_id=office.office_id)
        subject = _create_subject(session)
        term = _create_term(session, professor.user_id, subject.subject_id)

        students = [_create_student(session, f"s{i}@t.hr") for i in range(2)]
        tokens = [_login(client, s.email, "student123") for s in students]

        for tok in tokens:
            client.post(
                f"/termini/{term.term_id}/prijava", headers=_auth_headers(tok)
            )

        token = _login(client, students[0].email, "student123")
        response = client.get(
            f"/termini/{term.term_id}/popunjenost",
            headers=_auth_headers(token),
        )

        data = response.json()
        assert data["registered_students"] == 2
        assert data["free_places"] == 1
        assert data["full"] is False

    def test_popunjen_termin(self, client: TestClient, session: Session):
        office = _create_office(session, capacity=2)
        professor = _create_professor(session, office_id=office.office_id)
        subject = _create_subject(session)
        term = _create_term(session, professor.user_id, subject.subject_id)

        students = [_create_student(session, f"s{i}@t.hr") for i in range(2)]
        tokens = [_login(client, s.email, "student123") for s in students]

        for tok in tokens:
            client.post(
                f"/termini/{term.term_id}/prijava", headers=_auth_headers(tok)
            )

        token = _login(client, students[0].email, "student123")
        response = client.get(
            f"/termini/{term.term_id}/popunjenost",
            headers=_auth_headers(token),
        )

        data = response.json()
        assert data["registered_students"] == 2
        assert data["free_places"] == 0
        assert data["full"] is True

    def test_nepostojeci_termin_vraca_404(self, client: TestClient, session: Session):
        student = _create_student(session)
        token = _login(client, student.email, "student123")

        response = client.get(
            "/termini/9999/popunjenost",
            headers=_auth_headers(token),
        )
        assert response.status_code == 404

    def test_popunjenost_se_azurira_nakon_odjave(
        self, client: TestClient, session: Session
    ):
        office = _create_office(session, capacity=2)
        professor = _create_professor(session, office_id=office.office_id)
        subject = _create_subject(session)
        term = _create_term(session, professor.user_id, subject.subject_id)

        students = [_create_student(session, f"s{i}@t.hr") for i in range(2)]
        tokens = [_login(client, s.email, "student123") for s in students]

        for tok in tokens:
            client.post(
                f"/termini/{term.term_id}/prijava", headers=_auth_headers(tok)
            )

        # Popunjenost = 2/2
        r = client.get(
            f"/termini/{term.term_id}/popunjenost", headers=_auth_headers(tokens[0])
        )
        assert r.json()["full"] is True

        # Jedan se odjavi
        client.delete(
            f"/termini/{term.term_id}/prijava", headers=_auth_headers(tokens[0])
        )

        r2 = client.get(
            f"/termini/{term.term_id}/popunjenost", headers=_auth_headers(tokens[1])
        )
        assert r2.json()["full"] is False
        assert r2.json()["free_places"] == 1


# ---------------------------------------------------------------------------
# Integracijski scenarij
# ---------------------------------------------------------------------------


class TestIntegracija:
    """End-to-end scenariji koji kombiniraju više endpointa."""

    def test_cijeli_tok_prijave_odjave(self, client: TestClient, session: Session):
        """
        Scenarij:
        1. Student se prijavi na termin.
        2. Provjeri /me/prijave – termin je tu.
        3. Provjeri popunjenost – smanjen broj slobodnih mjesta.
        4. Student se odjavi.
        5. Provjeri /me/prijave – lista je prazna.
        6. Provjeri popunjenost – slobodna mjesta su obnovljena.
        """
        office = _create_office(session, capacity=3)
        professor = _create_professor(session, office_id=office.office_id)
        student = _create_student(session)
        subject = _create_subject(session)
        term = _create_term(session, professor.user_id, subject.subject_id)
        token = _login(client, student.email, "student123")
        headers = _auth_headers(token)

        # 1. Prijava
        r = client.post(f"/termini/{term.term_id}/prijava", headers=headers)
        assert r.status_code == 201

        # 2. /me/prijave
        r = client.get("/me/prijave", headers=headers)
        assert len(r.json()) == 1

        # 3. Popunjenost
        r = client.get(f"/termini/{term.term_id}/popunjenost", headers=headers)
        assert r.json()["registered_students"] == 1
        assert r.json()["free_places"] == 2

        # 4. Odjava
        r = client.delete(f"/termini/{term.term_id}/prijava", headers=headers)
        assert r.status_code == 200

        # 5. /me/prijave – prazno
        r = client.get("/me/prijave", headers=headers)
        assert r.json() == []

        # 6. Popunjenost – vraćena slobodna mjesta
        r = client.get(f"/termini/{term.term_id}/popunjenost", headers=headers)
        assert r.json()["registered_students"] == 0
        assert r.json()["free_places"] == 3

    def test_vise_studenata_razlicite_prijave(
        self, client: TestClient, session: Session
    ):
        """Svaki student vidi samo svoje prijave; popunjenost je globalna."""
        office = _create_office(session, capacity=10)
        professor = _create_professor(session, office_id=office.office_id)
        subject = _create_subject(session)
        term = _create_term(session, professor.user_id, subject.subject_id)

        studenti = [_create_student(session, f"s{i}@t.hr") for i in range(3)]
        tokeni = [_login(client, s.email, "student123") for s in studenti]

        for tok in tokeni:
            client.post(f"/termini/{term.term_id}/prijava", headers=_auth_headers(tok))

        for tok in tokeni:
            r = client.get("/me/prijave", headers=_auth_headers(tok))
            assert len(r.json()) == 1

        r = client.get(
            f"/termini/{term.term_id}/popunjenost", headers=_auth_headers(tokeni[0])
        )
        assert r.json()["registered_students"] == 3
