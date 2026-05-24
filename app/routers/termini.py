from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import (
    ConsultationTerm,
    ConsultationTermCreate,
    ConsultationTermRead,
    OccupancyResponse,
    TermRegistration,
    User,
)
from app.routers.auth import get_current_user, require_admin

router = APIRouter(prefix="/termini", tags=["termini"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _get_office_capacity(session: Session, term: ConsultationTerm) -> int:
    """Dohvati kapacitet ureda profesora."""
    professor = session.get(User, term.professor_id)
    if professor and professor.office_id:
        from app.models import Office

        office = session.get(Office, professor.office_id)
        if office:
            return office.capacity
    return 0


def _broj_prijava(session: Session, term_id: int) -> int:
    """Broji registracije za dani termin."""
    registracije = session.exec(
        select(TermRegistration).where(TermRegistration.term_id == term_id)
    ).all()
    return len(registracije)


def _termin_to_read(session: Session, term: ConsultationTerm) -> ConsultationTermRead:
    """Pretvori ConsultationTerm u ConsultationTermRead."""
    return ConsultationTermRead(
        term_id=term.term_id,
        professor_id=term.professor_id,
        subject_id=term.subject_id,
        start_time=term.start_time,
        end_time=term.end_time,
        created_at=term.created_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[ConsultationTermRead])
def list_termini(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ConsultationTermRead]:
    """Dohvati sve termine. Dostupno svim prijavljenim korisnicima."""
    termini = session.exec(select(ConsultationTerm)).all()
    return [_termin_to_read(session, t) for t in termini]


@router.get("/popunjenost/{termin_id}", response_model=OccupancyResponse)
def popunjenost_termina(
    termin_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> OccupancyResponse:
    """Dohvati popunjenost termina."""
    termin = session.get(ConsultationTerm, termin_id)
    if termin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Termin s ID-om {termin_id} nije pronađen.",
        )
    kapacitet = _get_office_capacity(session, termin)
    broj = _broj_prijava(session, termin_id)
    slobodna = max(0, kapacitet - broj)
    return OccupancyResponse(
        term_id=termin_id,
        capacity=kapacitet,
        registered_students=broj,
        free_places=slobodna,
        full=slobodna == 0,
    )


@router.get("/{termin_id}", response_model=ConsultationTermRead)
def get_termin(
    termin_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ConsultationTermRead:
    """Dohvati jedan termin po ID-u. Vraća 404 ako ne postoji."""
    termin = session.get(ConsultationTerm, termin_id)
    if termin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Termin s ID-om {termin_id} nije pronađen.",
        )
    return _termin_to_read(session, termin)


@router.post(
    "", response_model=ConsultationTermRead, status_code=status.HTTP_201_CREATED
)
def create_termin(
    payload: ConsultationTermCreate,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
) -> ConsultationTermRead:
    """Kreiraj novi termin. Samo admin ili profesor."""
    # Provjeri postoji li profesor
    profesor = session.get(User, payload.professor_id)
    if profesor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profesor s ID-om {payload.professor_id} nije pronađen.",
        )

    # Provjeri postoji li predmet
    from app.models import Subject

    predmet = session.get(Subject, payload.subject_id)
    if predmet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Predmet s ID-om {payload.subject_id} nije pronađen.",
        )

    # Provjeri da je start_time prije end_time
    if payload.start_time >= payload.end_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Početak termina mora biti prije kraja termina.",
        )

    novi_termin = ConsultationTerm(
        professor_id=payload.professor_id,
        subject_id=payload.subject_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    session.add(novi_termin)
    session.commit()
    session.refresh(novi_termin)
    return _termin_to_read(session, novi_termin)


@router.put("/{termin_id}", response_model=ConsultationTermRead)
def update_termin(
    termin_id: int,
    payload: ConsultationTermCreate,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
) -> ConsultationTermRead:
    """Uredi postojeći termin. Samo admin. Vraća 404 ako ne postoji."""
    termin = session.get(ConsultationTerm, termin_id)
    if termin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Termin s ID-om {termin_id} nije pronađen.",
        )

    if payload.start_time >= payload.end_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Početak termina mora biti prije kraja termina.",
        )

    termin.professor_id = payload.professor_id
    termin.subject_id = payload.subject_id
    termin.start_time = payload.start_time
    termin.end_time = payload.end_time

    session.add(termin)
    session.commit()
    session.refresh(termin)
    return _termin_to_read(session, termin)


@router.delete("/{termin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_termin(
    termin_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
) -> None:
    """Obriši termin. Samo admin. Vraća 404 ako ne postoji."""
    termin = session.get(ConsultationTerm, termin_id)
    if termin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Termin s ID-om {termin_id} nije pronađen.",
        )

    # Briši registracije vezane za termin
    registracije = session.exec(
        select(TermRegistration).where(TermRegistration.term_id == termin_id)
    ).all()
    for reg in registracije:
        session.delete(reg)

    session.delete(termin)
    session.commit()
