# Petar dio
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import jwt

from app.config import settings

# Bcrypt uses at most 72 bytes of password input. Keeping this explicit avoids
# silent truncation and makes future auth validation easier.
MAX_BCRYPT_PASSWORD_BYTES = 72


def _password_to_bytes(password: str) -> bytes:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError("Lozinka je preduga za bcrypt hashiranje.")
    return password_bytes


def hash_password(password: str) -> str:
    """Hash a plain-text password before saving it to the database."""

    password_bytes = _password_to_bytes(password)
    password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return password_hash.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plain password against a stored password hash."""

    try:
        password_bytes = _password_to_bytes(plain_password)
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except ValueError:
        return False


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token.

    TODO osoba 1:
    - after login works, call this with subject=user.email
    - include useful extra claims, for example {"role": user.role}
    """

    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expires_at}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
