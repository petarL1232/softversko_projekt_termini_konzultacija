from typing import Any

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import Office, OfficeRead, Subject, SubjectRead, User, UserRole
from app.routers.auth import get_current_user

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/professors")
def list_professors(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Read-only dropdown data for selecting professors in the UI.

    The UI shows professor names and office names, while API payloads still use IDs.
    """

    rows = session.exec(
        select(User, Office)
        .join(Office, User.office_id == Office.office_id, isouter=True)
        .where(User.role == UserRole.PROFESSOR)
        .order_by(User.last_name, User.first_name)
    ).all()

    return [
        {
            "user_id": professor.user_id,
            "first_name": professor.first_name,
            "last_name": professor.last_name,
            "email": professor.email,
            "role": professor.role,
            "office_id": professor.office_id,
            "office_name": office.office_name if office else None,
            "office_capacity": office.capacity if office else None,
        }
        for professor, office in rows
    ]


@router.get("/subjects", response_model=list[SubjectRead])
def list_subjects(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[Subject]:
    """Read-only dropdown data for selecting subjects in the UI."""

    subjects = session.exec(select(Subject).order_by(Subject.name)).all()

    return list(subjects)


@router.get("/offices", response_model=list[OfficeRead])
def list_offices(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[Office]:
    """Read-only dropdown data for selecting professor offices in the UI."""

    offices = session.exec(select(Office).order_by(Office.office_name)).all()

    return list(offices)
