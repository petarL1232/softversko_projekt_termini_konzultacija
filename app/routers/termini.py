from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import (
    Prijava,
    PrijavaStatus,
    Termin,
    TerminCreate,
    TerminRead,
    User,
)
from app.routers.auth import get_current_user, require_admin

router = APIRouter(prefix="/termini", tags=["termini"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _broj_aktivnih_prijava(session: Session, termin_id: int) -> int:
    """Broji samo ACTIVE prijave za dani termin."""
    prijave = session.exec(
        select(Prijava).where(
            Prijava.termin_id == termin_id,
            Prijava.status == PrijavaStatus.ACTIVE,
        )
    ).all()
    return len(prijave)


def _termin_to_read(session: Session, termin: Termin) -> TerminRead:
    """Pretvori Termin model u TerminRead s popunjenošću."""
    broj = _broj_aktivnih_prijava(session, termin.id)
    slobodna = termin.kapacitet - broj
    return TerminRead(
        id=termin.id,
        naziv=termin.naziv,
        opis=termin.opis,
        datum_vrijeme=termin.datum_vrijeme,
        kapacitet=termin.kapacitet,
        broj_prijava=broj,
        slobodna_mjesta=slobodna,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[TerminRead])
def list_termini(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[TerminRead]:
    """Dohvati sve termine s popunjenošću. Dostupno svim prijavljenim korisnicima."""
    termini = session.exec(select(Termin)).all()
    return [_termin_to_read(session, t) for t in termini]


@router.get("/{termin_id}", response_model=TerminRead)
def get_termin(
    termin_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TerminRead:
    """Dohvati jedan termin po ID-u. Vraća 404 ako ne postoji."""
    termin = session.get(Termin, termin_id)
    if termin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Termin s ID-om {termin_id} nije pronađen.",
        )
    return _termin_to_read(session, termin)


@router.post("", response_model=TerminRead, status_code=status.HTTP_201_CREATED)
def create_termin(
    payload: TerminCreate,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
) -> TerminRead:
    """Kreiraj novi termin. Samo admin."""
    novi_termin = Termin(
        naziv=payload.naziv,
        opis=payload.opis,
        datum_vrijeme=payload.datum_vrijeme,
        kapacitet=payload.kapacitet,
        created_by_id=admin.id,
    )
    session.add(novi_termin)
    session.commit()
    session.refresh(novi_termin)
    return _termin_to_read(session, novi_termin)


@router.put("/{termin_id}", response_model=TerminRead)
def update_termin(
    termin_id: int,
    payload: TerminCreate,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
) -> TerminRead:
    """Uredi postojeći termin. Samo admin. Vraća 404 ako ne postoji."""
    termin = session.get(Termin, termin_id)
    if termin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Termin s ID-om {termin_id} nije pronađen.",
        )

    termin.naziv = payload.naziv
    termin.opis = payload.opis
    termin.datum_vrijeme = payload.datum_vrijeme
    termin.kapacitet = payload.kapacitet

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
    """Obriši termin. Samo admin. Vraća 404 ako ne postoji.
    
    Briše i sve prijave vezane za taj termin.
    """
    termin = session.get(Termin, termin_id)
    if termin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Termin s ID-om {termin_id} nije pronađen.",
        )

    # Briši prijave vezane za termin prije brisanja termina
    prijave = session.exec(
        select(Prijava).where(Prijava.termin_id == termin_id)
    ).all()
    for prijava in prijave:
        session.delete(prijava)

    session.delete(termin)
    session.commit()
