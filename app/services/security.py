# Petar dio
import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.config import settings

# Koristio sam PBKDF2-HMAC-SHA256.
# To je SHA-256 bazirano hashiranje lozinki sa saltom i iteracijama.
# Nisam koristio obicni sha256(password), jer je to preslabo za lozinke.
# Umjesto toga:
# - za svakog korisnika generiramo poseban salt
# - koristimo puno iteracija
# - spremamo algoritam, broj iteracija, salt i hash u jedan string
# Format spremljenog hasha je u obliku:
# pbkdf2_sha256$iterations$salt_hex$hash_hex
# to je bitno za znati za decode
HASH_ALGORITHM = "sha256"
HASH_NAME = "pbkdf2_sha256"
HASH_ITERATIONS = 100_000
SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Hashira obicnu lozinku prije spremanja u bazu."""

    salt = os.urandom(SALT_BYTES)

    password_hash = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode("utf-8"),
        salt,
        HASH_ITERATIONS,
    )

    return (
        f"{HASH_NAME}$" f"{HASH_ITERATIONS}$" f"{salt.hex()}$" f"{password_hash.hex()}"
    )


def verify_password(plain_password: str, stored_password_hash: str) -> bool:
    """Provjerava odgovara li unesena lozinka spremljenom hashu."""

    try:
        hash_name, iterations_str, salt_hex, hash_hex = stored_password_hash.split("$")

        if hash_name != HASH_NAME:
            return False

        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)

        actual_hash = hashlib.pbkdf2_hmac(
            HASH_ALGORITHM,
            plain_password.encode("utf-8"),
            salt,
            iterations,
        )

        return hmac.compare_digest(actual_hash, expected_hash)

    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Kreira JWT access token.

    subject je najcesce user.email.
    extra_claims moze sadrzavati npr. {"role": user.role}.
    """

    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expires_at,
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Dekodira i provjerava JWT access token.

    Ako je token ispravan, vraca payload.
    Ako je token neispravan ili istekao, vraca None.
    """

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        return payload
    except JWTError:
        return None
