from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.database import get_session
from app.models import RegisterRequest, TokenResponse, User, UserRead, UserRole
from app.services.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def normalize_email(email: str) -> str:
    """najosnovnija normalizacija email adrese.

    Primjer:
    "  Test@Email.com  " -> "test@email.com"
    """

    return email.strip().lower()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_role_value(role: UserRole | str) -> str:
    """Return role as plain string for JWT payloads and comparisons."""

    if isinstance(role, UserRole):
        return role.value
    return role


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    """Vraca trenutno prijavljenog korisnika iz Bearer tokena."""

    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token nije ispravan ili je istekao.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = payload.get("sub")

    if not isinstance(email, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token nema ispravan subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = session.exec(select(User).where(User.email == email)).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Korisnik iz tokena vise ne postoji.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dopusta pristup samo admin korisniku."""

    if get_role_value(current_user.role) != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Samo admin ima pristup ovoj akciji.",
        )

    return current_user


def require_admin_or_professor(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dopusta pristup adminu ili profesoru."""

    role = get_role_value(current_user.role)
    allowed = {UserRole.ADMIN.value, UserRole.PROFESSOR.value}
    if role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Samo admin ili profesor ima pristup ovoj akciji.",
        )

    return current_user


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    payload: RegisterRequest,
    session: Session = Depends(get_session),
) -> User:
    """Registrira novog korisnika.

    Koraci:
    1. Ocisti email.
    2. Provjeri postoji li vec korisnik s tim emailom.
    3. Hashira lozinku.
    4. Spremi korisnika u bazu.
    5. Vrati korisnika bez password_hash polja.

    Obican register uvijek stvara role="student".
    Admin i professor korisnike dodajemo kroz seed/demo podatke ili admin rute.
    """

    email = normalize_email(payload.email)

    existing_user = session.exec(select(User).where(User.email == email)).first()

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Korisnik s tim emailom vec postoji.",
        )

    user = User(
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role=UserRole.STUDENT,
        office_id=None,
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return user


@router.post("/login", response_model=TokenResponse)
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
) -> TokenResponse:
    """Provjerava email i lozinku te vraca JWT access token.

    Swagger Authorize forma koristi polje 'username'.
    U nasem projektu username tretiramo kao email.
    """

    email = normalize_email(form_data.username)

    user = session.exec(select(User).where(User.email == email)).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neispravan email ili lozinka.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    password_is_valid = verify_password(form_data.password, user.password_hash)

    if not password_is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neispravan email ili lozinka.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=user.email,
        extra_claims={"role": get_role_value(user.role), "user_id": user.user_id},
    )

    return TokenResponse(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserRead)
# Vraca trenutno prijavljenog korisnika.
def read_me(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user
