from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.database import engine
from app.main import app
from app.models import Office, User, UserRole
from app.services.security import create_access_token, hash_password


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid4()}@example.com"


def create_user(
    session: Session,
    role: UserRole = UserRole.STUDENT,
    office_id: int | None = None,
) -> User:
    user = User(
        first_name="Test",
        last_name=role.value.title(),
        email=unique_email(role.value),
        password_hash=hash_password("StrongPass123!"),
        role=role,
        office_id=office_id,
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return user


def create_office(session: Session) -> Office:
    office = Office(
        office_name=f"Ured {uuid4()}",
        capacity=5,
    )

    session.add(office)
    session.commit()
    session.refresh(office)

    return office


def make_auth_headers(
    user_id: int,
    email: str,
    role: UserRole,
) -> dict[str, str]:
    token = create_access_token(
        subject=email,
        extra_claims={
            "role": role.value,
            "user_id": user_id,
        },
    )

    return {"Authorization": f"Bearer {token}"}


def test_admin_can_list_users() -> None:
    with TestClient(app) as client:
        with Session(engine) as session:
            admin = create_user(session, role=UserRole.ADMIN)
            admin_id = admin.user_id
            admin_email = admin.email
            assert admin_id is not None

        response = client.get(
            "/auth/users",
            headers=make_auth_headers(
                admin_id,
                admin_email,
                UserRole.ADMIN,
            ),
        )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_student_cannot_list_users() -> None:
    with TestClient(app) as client:
        with Session(engine) as session:
            student = create_user(session, role=UserRole.STUDENT)
            student_id = student.user_id
            student_email = student.email
            assert student_id is not None

        response = client.get(
            "/auth/users",
            headers=make_auth_headers(
                student_id,
                student_email,
                UserRole.STUDENT,
            ),
        )

    assert response.status_code == 403


def test_admin_can_promote_student_to_admin() -> None:
    with TestClient(app) as client:
        with Session(engine) as session:
            admin = create_user(session, role=UserRole.ADMIN)
            student = create_user(session, role=UserRole.STUDENT)

            admin_id = admin.user_id
            admin_email = admin.email
            student_id = student.user_id

            assert admin_id is not None
            assert student_id is not None

        response = client.patch(
            f"/auth/users/{student_id}/role",
            headers=make_auth_headers(
                admin_id,
                admin_email,
                UserRole.ADMIN,
            ),
            json={"role": "admin"},
        )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert response.json()["office_id"] is None


def test_admin_can_promote_student_to_professor_with_office() -> None:
    with TestClient(app) as client:
        with Session(engine) as session:
            admin = create_user(session, role=UserRole.ADMIN)
            student = create_user(session, role=UserRole.STUDENT)
            office = create_office(session)

            admin_id = admin.user_id
            admin_email = admin.email
            student_id = student.user_id
            office_id = office.office_id

            assert admin_id is not None
            assert student_id is not None
            assert office_id is not None

        response = client.patch(
            f"/auth/users/{student_id}/role",
            headers=make_auth_headers(
                admin_id,
                admin_email,
                UserRole.ADMIN,
            ),
            json={
                "role": "professor",
                "office_id": office_id,
            },
        )

    assert response.status_code == 200
    assert response.json()["role"] == "professor"
    assert response.json()["office_id"] == office_id


def test_admin_cannot_promote_professor_without_office() -> None:
    with TestClient(app) as client:
        with Session(engine) as session:
            admin = create_user(session, role=UserRole.ADMIN)
            student = create_user(session, role=UserRole.STUDENT)

            admin_id = admin.user_id
            admin_email = admin.email
            student_id = student.user_id

            assert admin_id is not None
            assert student_id is not None

        response = client.patch(
            f"/auth/users/{student_id}/role",
            headers=make_auth_headers(
                admin_id,
                admin_email,
                UserRole.ADMIN,
            ),
            json={"role": "professor"},
        )

    assert response.status_code == 400
    assert "Profesor mora imati" in response.json()["detail"]


def test_admin_demotes_professor_to_student_and_clears_office() -> None:
    with TestClient(app) as client:
        with Session(engine) as session:
            admin = create_user(session, role=UserRole.ADMIN)
            office = create_office(session)
            professor = create_user(
                session,
                role=UserRole.PROFESSOR,
                office_id=office.office_id,
            )

            admin_id = admin.user_id
            admin_email = admin.email
            professor_id = professor.user_id

            assert admin_id is not None
            assert professor_id is not None

        response = client.patch(
            f"/auth/users/{professor_id}/role",
            headers=make_auth_headers(
                admin_id,
                admin_email,
                UserRole.ADMIN,
            ),
            json={"role": "student"},
        )

    assert response.status_code == 200
    assert response.json()["role"] == "student"
    assert response.json()["office_id"] is None


def test_student_cannot_change_user_role() -> None:
    with TestClient(app) as client:
        with Session(engine) as session:
            actor = create_user(session, role=UserRole.STUDENT)
            target = create_user(session, role=UserRole.STUDENT)

            actor_id = actor.user_id
            actor_email = actor.email
            target_id = target.user_id

            assert actor_id is not None
            assert target_id is not None

        response = client.patch(
            f"/auth/users/{target_id}/role",
            headers=make_auth_headers(
                actor_id,
                actor_email,
                UserRole.STUDENT,
            ),
            json={"role": "admin"},
        )

    assert response.status_code == 403


def test_admin_cannot_remove_own_admin_role() -> None:
    with TestClient(app) as client:
        with Session(engine) as session:
            admin = create_user(session, role=UserRole.ADMIN)

            admin_id = admin.user_id
            admin_email = admin.email

            assert admin_id is not None

        response = client.patch(
            f"/auth/users/{admin_id}/role",
            headers=make_auth_headers(
                admin_id,
                admin_email,
                UserRole.ADMIN,
            ),
            json={"role": "student"},
        )

    assert response.status_code == 400
    assert "sam sebi" in response.json()["detail"]


def test_admin_role_update_unknown_user_returns_404() -> None:
    with TestClient(app) as client:
        with Session(engine) as session:
            admin = create_user(session, role=UserRole.ADMIN)

            admin_id = admin.user_id
            admin_email = admin.email

            assert admin_id is not None

        response = client.patch(
            "/auth/users/999999/role",
            headers=make_auth_headers(
                admin_id,
                admin_email,
                UserRole.ADMIN,
            ),
            json={"role": "admin"},
        )

    assert response.status_code == 404


def test_admin_role_update_invalid_role_returns_422() -> None:
    with TestClient(app) as client:
        with Session(engine) as session:
            admin = create_user(session, role=UserRole.ADMIN)
            student = create_user(session, role=UserRole.STUDENT)

            admin_id = admin.user_id
            admin_email = admin.email
            student_id = student.user_id

            assert admin_id is not None
            assert student_id is not None

        response = client.patch(
            f"/auth/users/{student_id}/role",
            headers=make_auth_headers(
                admin_id,
                admin_email,
                UserRole.ADMIN,
            ),
            json={"role": "superadmin"},
        )

    assert response.status_code == 422
