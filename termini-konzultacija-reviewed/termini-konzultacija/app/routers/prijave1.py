

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from models import (
    Prijava,
    PrijavaStatus,
    Termin,
    TerminRead,
    PopunjenostResponse,
    User,
)
from dependencies import get_current_user, get_session  # prilagodi importu u projektu

router = APIRouter(tags=["prijave"])


def _count_active_prijave(session: Session, termin_id: int) -> int:
    """Pomoćna funkcija — broji samo ACTIVE prijave za termin."""
    prijave = session.exec(
        select(Prijava).where(
            Prijava.termin_id == termin_id,
            Prijava.status == PrijavaStatus.ACTIVE,
        )
    ).all()
    return len(prijave)


@router.post("/termini/{termin_id}/prijava", status_code=201, response_model=TerminRead)
def prijavi_se_na_termin(
    termin_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> TerminRead:
    """Prijava trenutno prijavljenog korisnika na termin."""

    # 1. Provjeri postoji li termin
    termin = session.get(Termin, termin_id)
    if not termin:
        raise HTTPException(status_code=404, detail="Termin nije pronađen.")

    # 2. Provjeri duplikat — korisnik već ima ACTIVE prijavu za ovaj termin
    postojeca = session.exec(
        select(Prijava).where(
            Prijava.user_id == current_user.id,
            Prijava.termin_id == termin_id,
            Prijava.status == PrijavaStatus.ACTIVE,
        )
    ).first()
    if postojeca:
        raise HTTPException(
            status_code=409,
            detail="Već ste prijavljeni na ovaj termin.",
        )

    # 3. Provjeri kapacitet
    broj_prijava = _count_active_prijave(session, termin_id)
    if broj_prijava >= termin.kapacitet:
        raise HTTPException(
            status_code=409,
            detail="Termin je popunjen.",
        )

    # 4. Kreiraj prijavu
    nova_prijava = Prijava(
        user_id=current_user.id,
        termin_id=termin_id,
        status=PrijavaStatus.ACTIVE,
    )
    session.add(nova_prijava)
    session.commit()

    return TerminRead(
        id=termin.id,
        naziv=termin.naziv,
        opis=termin.opis,
        datum_vrijeme=termin.datum_vrijeme,
        kapacitet=termin.kapacitet,
        broj_prijava=broj_prijava + 1,
        slobodna_mjesta=termin.kapacitet - (broj_prijava + 1),
    )


@router.delete("/termini/{termin_id}/prijava", status_code=200)
def odjavi_se_s_termina(
    termin_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Odjava korisnika s termina — postavlja status na CANCELLED."""

    # Pronađi aktivnu prijavu ovog korisnika za traženi termin
    prijava = session.exec(
        select(Prijava).where(
            Prijava.user_id == current_user.id,
            Prijava.termin_id == termin_id,
            Prijava.status == PrijavaStatus.ACTIVE,
        )
    ).first()

    if not prijava:
        raise HTTPException(
            status_code=404,
            detail="Nemate aktivnu prijavu za ovaj termin.",
        )

    # samo promijeni status, ne briši zapis
    prijava.status = PrijavaStatus.CANCELLED
    session.add(prijava)
    session.commit()

    return {"message": "Uspješno ste se odjavili s termina."}


@router.get("/me/prijave", response_model=list[TerminRead])
def moje_prijave(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[TerminRead]:
    """Vraća sve termine na koje je trenutni korisnik aktivno prijavljen."""

    prijave = session.exec(
        select(Prijava).where(
            Prijava.user_id == current_user.id,
            Prijava.status == PrijavaStatus.ACTIVE,
        )
    ).all()

    result = []
    for prijava in prijave:
        termin = session.get(Termin, prijava.termin_id)
        if not termin:
            continue  # obrisani termin, preskoči

        broj_prijava = _count_active_prijave(session, termin.id)
        result.append(
            TerminRead(
                id=termin.id,
                naziv=termin.naziv,
                opis=termin.opis,
                datum_vrijeme=termin.datum_vrijeme,
                kapacitet=termin.kapacitet,
                broj_prijava=broj_prijava,
                slobodna_mjesta=termin.kapacitet - broj_prijava,
            )
        )

    return result


@router.get("/termini/{termin_id}/popunjenost", response_model=PopunjenostResponse)
def popunjenost_termina(
    termin_id: int,
    session: Session = Depends(get_session),
) -> PopunjenostResponse:
    """Vraća informacije o popunjenosti termina — javni endpoint, bez autentikacije."""

    termin = session.get(Termin, termin_id)
    if not termin:
        raise HTTPException(status_code=404, detail="Termin nije pronađen.")

    broj_prijava = _count_active_prijave(session, termin_id)
    slobodna_mjesta = termin.kapacitet - broj_prijava

    return PopunjenostResponse(
        termin_id=termin.id,
        kapacitet=termin.kapacitet,
        broj_prijava=broj_prijava,
        slobodna_mjesta=slobodna_mjesta,
        popunjen=slobodna_mjesta <= 0,
    )