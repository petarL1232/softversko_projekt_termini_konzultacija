from pathlib import Path

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

# Router za sve endpointe vezane uz prijave na termine.
# Tag "prijave" grupira ove rute u Swagger dokumentaciji.
router = APIRouter(tags=["prijave"])


# -------------------------------------------------------
# Pomoćne (helper) funkcije
# -------------------------------------------------------

def _get_office_capacity(session: Session, term: ConsultationTerm) -> int:
    """
    Vraća kapacitet ureda profesora koji drži zadani termin.

    Dohvaća profesora prema term.professor_id, zatim njegov ured,
    i vraća office.capacity. Ako profesor nema ured ili ured nije
    pronađen, vraća 0 (što će blokirati sve prijave).
    """
    professor = session.get(User, term.professor_id)
    if professor and professor.office_id:
        office = session.get(Office, professor.office_id)
        if office:
            return office.capacity
    return 0


def _broj_prijava(session: Session, term_id: int) -> int:
    """
    Vraća trenutni broj prijavljenih studenata na zadani termin.

    Dohvaća sve TermRegistration zapise s danim term_id
    i broji ih — to je trenutna popunjenost termina.
    """
    regs = session.exec(
        select(TermRegistration).where(TermRegistration.term_id == term_id)
    ).all()
    return len(regs)


# -------------------------------------------------------
# Favicon endpoint (nema veze s prijavama, ali mora biti
# negdje registriran — stavili smo ga ovdje jer je ovaj
# router registriran zadnji u main.py)
# -------------------------------------------------------

@router.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """
    Servira favicon.png iz app/static foldera.
    include_in_schema=False znači da se ne prikazuje u Swaggeru.
    Ako datoteka ne postoji, vraća 404.
    """
    static_dir = Path(__file__).resolve().parent.parent / "static"
    fav = static_dir / "favicon.png"
    if fav.exists():
        return FileResponse(fav, media_type="image/png")
    return Response(status_code=status.HTTP_404_NOT_FOUND)


# -------------------------------------------------------
# POST /termini/{termin_id}/prijava
# Prijava studenta na termin
# -------------------------------------------------------

@router.post(
    "/termini/{termin_id}/prijava",
    status_code=status.HTTP_201_CREATED,
    response_model=TermRegistrationRead,
)
def prijavi_se_na_termin(
    termin_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),  # JWT autentikacija
) -> TermRegistration:
    """
    Prijavljuje trenutno prijavljenog korisnika (studenta) na termin.

    Provjere koje se rade redom:
      1. Postoji li termin s tim ID-om? → 404 ako ne.
      2. Je li korisnik već prijavljen? → 409 Conflict ako jest.
      3. Je li termin pun (broj prijava >= kapacitet ureda)? → 409 Conflict.

    Ako sve provjere prođu, kreira novi TermRegistration zapis u bazi.
    """

    # 1. Dohvati termin iz baze — ako ne postoji, vrati 404
    termin = session.get(ConsultationTerm, termin_id)
    if termin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Termin s ID-om {termin_id} nije pronađen.",
        )

    # 2. Provjeri je li korisnik već prijavljen na ovaj termin
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

    # 3. Provjeri kapacitet — ako je termin pun ili kapacitet nije postavljen, blokiraj
    kapacitet = _get_office_capacity(session, termin)
    broj = _broj_prijava(session, termin_id)
    if kapacitet <= 0 or broj >= kapacitet:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Termin je popunjen ili kapacitet nije postavljen.",
        )

    # Sve provjere prošle — kreiraj prijavu i spremi u bazu
    reg = TermRegistration(term_id=termin_id, student_id=current_user.user_id)
    session.add(reg)
    session.commit()
    session.refresh(reg)  # osvježi objekt da dobijemo auto-generirani registration_id
    return reg


# -------------------------------------------------------
# DELETE /termini/{termin_id}/prijava
# Odjava studenta s termina
# -------------------------------------------------------

@router.delete("/termini/{termin_id}/prijava")
def odjavi_se_s_termina(
    termin_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),  # JWT autentikacija
) -> dict[str, object]:
    """
    Odjavljuje trenutno prijavljenog korisnika s termina.

    Traži TermRegistration zapis koji odgovara kombinaciji
    (termin_id, current_user.user_id). Ako zapis ne postoji,
    korisnik nije bio prijavljen → 404.

    Ako postoji, briše zapis i vraća poruku potvrde.
    """

    # Pronađi prijavu za ovog korisnika na ovom terminu
    reg = session.exec(
        select(TermRegistration).where(
            TermRegistration.term_id == termin_id,
            TermRegistration.student_id == current_user.user_id,
        )
    ).first()

    # Ako prijava ne postoji, korisnik nije bio prijavljen → 404
    if reg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Korisnik nije prijavljen na ovaj termin.",
        )

    # Obriši prijavu i potvrdi brisanje
    session.delete(reg)
    session.commit()
    return {"message": "Odjava uspješna.", "termin_id": termin_id}


# -------------------------------------------------------
# GET /me/prijave
# Lista svih termina na koje je prijavljeni korisnik prijavljen
# -------------------------------------------------------

@router.get("/me/prijave")
def moje_prijave(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),  # JWT autentikacija
) -> list[dict[str, object]]:
    """
    Vraća listu svih prijava trenutnog korisnika.

    Za svaku TermRegistration dohvaća i podatke o terminu
    (ConsultationTerm) i vraća ih zajedno kao ugniježđeni objekt.
    Ako termin iz nekog razloga ne postoji (obrisana baza?),
    polje "termin" će biti None umjesto da pukne request.
    """

    # Dohvati sve prijave za ovog korisnika
    regs = session.exec(
        select(TermRegistration).where(
            TermRegistration.student_id == current_user.user_id
        )
    ).all()

    # Za svaku prijavu dohvati i podatke o terminu
    result: list[dict[str, object]] = []
    for r in regs:
        term = session.get(ConsultationTerm, r.term_id)
        result.append(
            {
                "registration_id": r.registration_id,
                "registered_at": r.registered_at,
                # Ugniježđeni objekt s podacima termina (ili None ako termin ne postoji)
                "termin": {
                    "term_id": term.term_id,
                    "professor_id": term.professor_id,
                    "subject_id": term.subject_id,
                    "start_time": term.start_time,
                    "end_time": term.end_time,
                    "created_at": term.created_at,
                }
                if term
                else None,
            }
        )
    return result


# -------------------------------------------------------
# GET /termini/{termin_id}/popunjenost
# Informacije o popunjenosti termina (javni endpoint — bez auth)
# -------------------------------------------------------

@router.get("/termini/{termin_id}/popunjenost", response_model=OccupancyResponse)
def popunjenost_termina(
    termin_id: int,
    session: Session = Depends(get_session),
    # Nema get_current_user — ovaj endpoint je javan, bez JWT-a
) -> OccupancyResponse:
    """
    Vraća podatke o popunjenosti termina: kapacitet, broj prijavljenih,
    broj slobodnih mjesta i je li termin pun.

    Ovaj endpoint je namjerno javan (bez autentikacije) kako bi
    studenti mogli vidjeti popunjenost bez da se moraju prijaviti.
    """

    # Provjeri postoji li termin
    termin = session.get(ConsultationTerm, termin_id)
    if termin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Termin s ID-om {termin_id} nije pronađen.",
        )

    # Izračunaj slobodna mjesta (min 0 — ne može biti negativno)
    kapacitet = _get_office_capacity(session, termin)
    broj = _broj_prijava(session, termin_id)
    slobodna = max(0, kapacitet - broj)

    return OccupancyResponse(
        term_id=termin_id,
        capacity=kapacitet,
        registered_students=broj,
        free_places=slobodna,
        full=slobodna == 0,  # True ako nema slobodnih mjesta
    )