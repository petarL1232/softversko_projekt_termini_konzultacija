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
    """Najosnovnija normalizacija email adrese.

    Primjer: " Test@Email.com " -> "test@email.com"
    """

    return email.strip().lower()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

PASSWORD_MIN_LENGTH = 12
PASSWORD_SPECIAL_CHARS = set("!@#$%^&*()-_=+[]{};:,.?/\\|`~<>\"'")

COMMON_PASSWORD_BLOCKLIST = {
    "123456",
    "1234567",
    "12345678",
    "123456789",
    "1234567890",
    "111111",
    "000000",
    "password",
    "password1",
    "password12",
    "password123",
    "password1234",
    "password12345",
    "password123456",
    "qwerty",
    "qwerty1",
    "qwerty12",
    "qwerty123",
    "qwerty1234",
    "qwerty12345",
    "qwerty123456",
    "admin",
    "admin1",
    "admin12",
    "admin123",
    "admin1234",
    "admin12345",
    "admin123456",
    "welcome",
    "welcome1",
    "welcome12",
    "welcome123",
    "welcome1234",
    "welcome12345",
    "letmein",
    "letmein123",
    "changeme",
    "changeme123",
    "default",
    "default123",
    "test",
    "test123",
    "test1234",
    "test12345",
    "student",
    "student1",
    "student12",
    "student123",
    "student1234",
    "student12345",
    "profesor",
    "profesor123",
    "professor",
    "professor123",
    "mathos",
    "mathos123",
    "osijek",
    "osijek123",
    "lozinka",
    "lozinka1",
    "lozinka12",
    "lozinka123",
    "lozinka1234",
    "lozinka12345",
}

LEET_TRANSLATION = str.maketrans(
    {
        "@": "a",
        "$": "s",
        "0": "o",
    }
)


def normalize_password_for_blocklist(password: str) -> set[str]:
    """Vraca varijante lozinke za usporedbu s blocklistom.

    Primjeri:
    - " Password123! " daje varijante koje hvataju password123
    - "P@ssw0rd123!" daje varijantu password123
    """

    lowered = password.strip().lower()

    leet_lowered = lowered.translate(LEET_TRANSLATION)

    alnum_only = "".join(char for char in lowered if char.isalnum())
    leet_alnum_only = "".join(char for char in leet_lowered if char.isalnum())

    return {
        lowered,
        leet_lowered,
        alnum_only,
        leet_alnum_only,
    }

def validate_password_not_common(password: str) -> None:
    """Odbija ceste ili lako pogodne lozinke za nove registracije.

    Provjera se koristi samo kod registracije.
    Postojeci korisnici i demo/admin login nisu pogodeni 
    jer login ne poziva ovu funkciju.
    """

    password_variants = normalize_password_for_blocklist(password)

    if password_variants.intersection(COMMON_PASSWORD_BLOCKLIST):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Lozinka je na listi cestih lozinki ili je previse lako pogodiva. "
                "Odaberite jedinstvenu lozinku."
            ),
        )


def validate_password_strength(password: str) -> None:
    """Provjerava password policy za nove registracije.

    Ovo se koristi samo kod registracije novih korisnika.
    Login ne koristi ovu provjeru, tako da postojeci demo korisnici
    i stari hashirani passwordi i dalje rade.
    """

    missing_rules: list[str] = []

    if len(password) < PASSWORD_MIN_LENGTH:
        missing_rules.append("najmanje 12 znakova")

    if not any(char.isupper() for char in password):
        missing_rules.append("barem jedno veliko slovo")

    if not any(char.islower() for char in password):
        missing_rules.append("barem jedno malo slovo")

    if not any(char.isdigit() for char in password):
        missing_rules.append("barem jedan broj")

    if not any(char in PASSWORD_SPECIAL_CHARS for char in password):
        missing_rules.append("barem jedan specijalni znak")

    if missing_rules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Lozinka nije dovoljno jaka. Mora imati: "
                + ", ".join(missing_rules)
                + "."
            ),
        )


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
    2. Provjeri je li lozinka na listi cestih lozinki.
    3. Provjeri password policy za novu lozinku.
    4. Provjeri postoji li vec korisnik s tim emailom.
    5. Hashira lozinku.
    6. Spremi korisnika u bazu.
    7. Vrati korisnika bez password_hash polja.

    Obican register uvijek stvara role="student".
    Admin i professor korisnike dodajemo kroz seed/demo podatke ili admin rute.
    """

    email = normalize_email(payload.email)

    validate_password_not_common(payload.password)
    validate_password_strength(payload.password)

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
def read_me(
    current_user: User = Depends(get_current_user),
) -> User:
    """Vraca trenutno prijavljenog korisnika."""

    return current_user
