# Petar dio
from app.services.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_does_not_return_plain_password() -> None:
    plain_password = "test123"

    password_hash = hash_password(plain_password)

    assert password_hash != plain_password
    assert password_hash.startswith("pbkdf2_sha256$")


def test_verify_password_accepts_correct_password() -> None:
    plain_password = "test123"

    password_hash = hash_password(plain_password)

    assert verify_password(plain_password, password_hash) is True


def test_verify_password_rejects_wrong_password() -> None:
    plain_password = "test123"

    password_hash = hash_password(plain_password)

    assert verify_password("wrong-password", password_hash) is False


def test_hash_password_uses_different_salt_for_same_password() -> None:
    plain_password = "test123"

    first_hash = hash_password(plain_password)
    second_hash = hash_password(plain_password)

    assert first_hash != second_hash
    assert verify_password(plain_password, first_hash) is True
    assert verify_password(plain_password, second_hash) is True


def test_decode_access_token_returns_payload() -> None:
    token = create_access_token(
        subject="student@example.com",
        extra_claims={"role": "user"},
    )

    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "student@example.com"
    assert payload["role"] == "user"


def test_decode_access_token_rejects_invalid_token() -> None:
    payload = decode_access_token("not-a-real-token")

    assert payload is None
