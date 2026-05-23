from fastapi import APIRouter

router = APIRouter(tags=["prijave"])


@router.post("/termini/{termin_id}/prijava", status_code=201)
def prijavi_se_na_termin(termin_id: int) -> dict[str, object]:
    """Skeleton endpoint for term signup.

    TODO osoba 4:
    - dodati get_current_user dependency
    - provjeriti postoji li termin
    - provjeriti je li korisnik vec aktivno prijavljen
    - provjeriti je li broj aktivnih prijava manji od kapaciteta
    - ako je sve ok, kreirati Prijava(status=ACTIVE)
    """

    return {
        "message": "TODO: implementirati prijavu na termin",
        "termin_id": termin_id,
    }


@router.delete("/termini/{termin_id}/prijava")
def odjavi_se_s_termina(termin_id: int) -> dict[str, object]:
    """Skeleton endpoint for term cancellation.

    TODO osoba 4:
    - naci aktivnu prijavu trenutnog korisnika za ovaj termin
    - ako ne postoji, vratiti 404 ili 409
    - postaviti status=CANCELLED umjesto fizickog brisanja
    """

    return {
        "message": "TODO: implementirati odjavu s termina",
        "termin_id": termin_id,
    }


@router.get("/me/prijave")
def moje_prijave() -> list[dict[str, object]]:
    """Skeleton endpoint for current user's signups.

    TODO osoba 4:
    - vratiti sve aktivne prijave trenutnog korisnika
    - uz prijavu vratiti i podatke termina
    """

    return []


@router.get("/termini/{termin_id}/popunjenost")
def popunjenost_termina(termin_id: int) -> dict[str, object]:
    """Skeleton endpoint for occupancy.

    TODO osoba 4:
    - dohvatiti termin ili vratiti 404
    - izbrojati samo ACTIVE prijave
    - izracunati slobodna_mjesta = kapacitet - broj_prijava
    """

    return {
        "termin_id": termin_id,
        "kapacitet": 0,
        "broj_prijava": 0,
        "slobodna_mjesta": 0,
        "popunjen": False,
        "message": "TODO: implementirati izračun popunjenosti",
    }
