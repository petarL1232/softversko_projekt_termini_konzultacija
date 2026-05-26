from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import Subject, SubjectRead, User, UserRead, UserRole
from app.routers.auth import get_current_user

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/professors", response_model=list[UserRead])
def list_professors(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[User]:
    """Read-only dropdown data for selecting professors in the UI."""

    professors = session.exec(
        select(User)
        .where(User.role == UserRole.PROFESSOR)
        .order_by(User.last_name, User.first_name)
    ).all()

    return list(professors)


@router.get("/subjects", response_model=list[SubjectRead])
def list_subjects(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[Subject]:
    """Read-only dropdown data for selecting subjects in the UI."""

    subjects = session.exec(select(Subject).order_by(Subject.name)).all()

    return list(subjects)
