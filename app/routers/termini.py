from fastapi import APIRouter, HTTPException, status

from app.models import TerminCreate

router = APIRouter(prefix="/termini", tags=["termini"])


@router.get("")
def list_termini() -> list[dict[str, object]]:
    """Skeleton endpoint for listing terms.

    TODO osoba 3:
    - dohvatiti sve termine iz baze
    - za svaki termin izracunati broj aktivnih prijava
    - vratiti kapacitet, broj_prijava i slobodna_mjesta
    """

    return []


@router.get("/{termin_id}")
def get_termin(termin_id: int) -> dict[str, object]:
    """Skeleton endpoint for one term.

    TODO osoba 3:
    - ako termin ne postoji, vratiti 404
    - ako postoji, vratiti podatke termina + popunjenost
    """

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"TODO: dohvatiti termin {termin_id}",
    )


@router.post("", status_code=201)
def create_termin(payload: TerminCreate) -> dict[str, object]:
    """Skeleton endpoint for creating terms.

    TODO osoba 3:
    - dodati require_admin dependency
    - validacija je djelomicno vec u TerminCreate modelu
    - spremiti novi Termin u bazu
    """

    return {
        "message": "TODO: implementirati admin kreiranje termina",
        "termin": payload.model_dump(),
    }


@router.put("/{termin_id}")
def update_termin(termin_id: int, payload: TerminCreate) -> dict[str, object]:
    """Skeleton endpoint for updating terms.

    TODO osoba 3:
    - dodati require_admin dependency
    - pronaci termin ili vratiti 404
    - promijeniti naziv/opis/datum_vrijeme/kapacitet
    """

    return {
        "message": f"TODO: implementirati uređivanje termina {termin_id}",
        "termin": payload.model_dump(),
    }


@router.delete("/{termin_id}")
def delete_termin(termin_id: int) -> dict[str, object]:
    """Skeleton endpoint for deleting terms.

    TODO osoba 3:
    - dodati require_admin dependency
    - pronaci termin ili vratiti 404
    - odluciti brisu li se i prijave na taj termin ili se blokira brisanje
    """

    return {"message": f"TODO: implementirati brisanje termina {termin_id}"}
