from fastapi import APIRouter

from app.models import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register_user(payload: RegisterRequest) -> dict[str, str]:
    """Skeleton endpoint for user registration.

    TODO osoba 1:
    - provjeriti postoji li korisnik s istim emailom
    - hashirati lozinku pomocu hash_password()
    - spremiti User u bazu
    - vratiti jasnu poruku ili korisnika bez password_hash polja
    """

    return {
        "message": "TODO: implementirati registraciju korisnika",
        "email": payload.email,
    }


@router.post("/login", response_model=TokenResponse)
def login_user(payload: LoginRequest) -> TokenResponse:
    """Skeleton endpoint for user login.

    TODO osoba 1:
    - pronaci korisnika po emailu
    - provjeriti lozinku pomocu verify_password()
    - napraviti JWT pomocu create_access_token()
    - u token staviti barem sub=user.email i role=user.role
    """

    return TokenResponse(access_token=f"TODO_TOKEN_FOR_{payload.email}")


@router.get("/me")
def read_me() -> dict[str, str]:
    """Skeleton endpoint for current user.

    TODO osoba 1:
    - napraviti get_current_user dependency
    - iz Bearer tokena procitati korisnika
    - vratiti email i role trenutno prijavljenog korisnika
    """

    return {"message": "TODO: vratiti trenutno prijavljenog korisnika"}
