"""
Osoba 4 – Prijave / odjave s konzultacijskih termina.

Endpointi:
  POST   /termini/{termin_id}/prijava         – prijava studenta na termin
  DELETE /termini/{termin_id}/prijava         – odjava studenta s termina
  GET    /me/prijave                          – pregled vlastitih prijava
  GET    /termini/{termin_id}/popunjenost     – popunjenost termina (javno)
"""

from pathlib

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, Response
from sqlmodel import Session, select

from app.database import get_session
from app.models import (
    ConsultationTerm,
    Office,
    OccupancyResponse,
    TermRegistration,
    TermRegistrationRead,
    User,
)
from app.routers.auth import get_current_user

router = APIRouter(tags=["prijave"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_office_capacity(session: Session, term: ConsultationTerm) -> int:
    """Vraća kapacitet ureda profesora koji drži termin, ili 0 ako nije postavljen."""
    professor = session.get(User, term.professor_id)
    if professor and professor.office_id:
        office = session.get(Office, professor.office_id)
        if office:
            return office.capacity
    return 0


def _broj_prijava(session: Session, term_id: int) -> int:
    """Broji koliko je studenata prijavljeno na dani termin."""
    regs = session.exec(
        select(TermRegistration).where(TermRegistration.term_id == term_id)
    ).all()
    return len(regs)


def _get_term_or_404(session: Session, termin_id: int) -> ConsultationTerm:
    """Dohvati termin po ID-u ili baci 404."""
    termin = session.get(ConsultationTerm, termin_id)
    if termin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Termin s ID-om {termin_id} nije pronađen.",
        )
    return termin


# ---------------------------------------------------------------------------
# Favicon – izbjegava loganje 404 grešaka za favicon.ico
# ---------------------------------------------------------------------------


@router.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    static_dir = Path(__file__).resolve().parent.parent / "static"
    fav = static_dir / "favicon.png"
    if fav.exists():
        return FileResponse(fav, media_type="image/png")
    return Response(status_code=status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Prijava na termin
# ---------------------------------------------------------------------------


@router.post(
    "/termini/{termin_id}/prijava",
    status_code=status.HTTP_201_CREATED,
    response_model=TermRegistrationRead,
    summary="Prijava studenta na konzultacijski termin",
)
def prijavi_se_na_termin(
    termin_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TermRegistration:
    """
    Prijavi trenutno prijavljenog korisnika na konzultacijski termin.

    Mogući statusni kodovi:
    - **201** – prijava uspješna
    - **401** – korisnik nije autentificiran
    - **404** – termin ne postoji
    - **409** – korisnik je već prijavljen ili je termin popunjen
    """
    termin = _get_term_or_404(session, termin_id)

    # Provjeri nije li student već prijavljen
    existing = session.exec(
        select(TermRegistration).where(
            TermRegistration.term_id == termin_id,
            TermRegistration.student_id == current_user.user_id,
        )
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Korisnik je već prijavljen na ovaj termin.",
        )

    # Provjeri kapacitet
    kapacitet = _get_office_capacity(session, termin)
    broj = _broj_prijava(session, termin_id)
    if kapacitet <= 0 or broj >= kapacitet:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Termin je popunjen ili kapacitet nije postavljen.",
        )

    reg = TermRegistration(term_id=termin_id, student_id=current_user.user_id)
    session.add(reg)
    session.commit()
    session.refresh(reg)
    return reg


# ---------------------------------------------------------------------------
# Odjava s termina
# ---------------------------------------------------------------------------


@router.delete(
    "/termini/{termin_id}/prijava",
    summary="Odjava studenta s konzultacijskog termina",
)
def odjavi_se_s_termina(
    termin_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """
    Odjavi trenutno prijavljenog korisnika s konzultacijskog termina.

    Mogući statusni kodovi:
    - **200** – odjava uspješna
    - **401** – korisnik nije autentificiran
    - **404** – termin ne postoji ili korisnik nije prijavljen
    """
    # Provjeri postoji li termin (vraća 404 ako ne postoji)
    _get_term_or_404(session, termin_id)

    reg = session.exec(
        select(TermRegistration).where(
            TermRegistration.term_id == termin_id,
            TermRegistration.student_id == current_user.user_id,
        )
    ).first()
    if reg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Korisnik nije prijavljen na ovaj termin.",
        )

    session.delete(reg)
    session.commit()
    return {"message": "Odjava uspješna.", "termin_id": termin_id}


# ---------------------------------------------------------------------------
# Pregled vlastitih prijava
# ---------------------------------------------------------------------------


@router.get(
    "/me/prijave",
    summary="Prikaz svih termina na koje je student prijavljen",
)
def moje_prijave(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, object]]:
    """
    Vrati listu svih konzultacijskih termina na koje je trenutni korisnik prijavljen.

    Svaki element liste sadrži:
    - `registration_id` – ID prijave
    - `registered_at` – kada se prijavilo
    - `termin` – detalji termina (ili `null` ako je termin obrisan)
    """
    regs = session.exec(
        select(TermRegistration).where(
            TermRegistration.student_id == current_user.user_id
        )
    ).all()

    result: list[dict[str, object]] = []
    for r in regs:
        term = session.get(ConsultationTerm, r.term_id)
        result.append(
            {
                "registration_id": r.registration_id,
                "registered_at": r.registered_at,
                "termin": (
                    {
                        "term_id": term.term_id,
                        "professor_id": term.professor_id,
                        "subject_id": term.subject_id,
                        "start_time": term.start_time,
                        "end_time": term.end_time,
                        "created_at": term.created_at,
                    }
                    if term
                    else None
                ),
            }
        )
    return result


# ---------------------------------------------------------------------------
# Popunjenost termina
# ---------------------------------------------------------------------------


@router.get(
    "/termini/{termin_id}/popunjenost",
    response_model=OccupancyResponse,
    summary="Provjera popunjenosti konzultacijskog termina",
)
def popunjenost_termina(
    termin_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> OccupancyResponse:
    """
    Vrati informacije o popunjenosti termina:
    - `capacity` – ukupan kapacitet ureda
    - `registered_students` – broj prijavljenih studenata
    - `free_places` – broj slobodnih mjesta
    - `full` – je li termin popunjen

    Mogući statusni kodovi:
    - **200** – uspješno
    - **401** – korisnik nije autentificiran
    - **404** – termin ne postoji
    """
    termin = _get_term_or_404(session, termin_id)
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
