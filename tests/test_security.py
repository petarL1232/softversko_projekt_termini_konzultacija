# Petar dio
import pytest

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


def test_hash_password_has_expected_storage_format() -> None:
    password_hash = hash_password("test123")

    parts = password_hash.split("$")

    assert len(parts) == 4
    assert parts[0] == "pbkdf2_sha256"
    assert int(parts[1]) >= 100_000

    # Salt i hash moraju biti validni hex stringovi.
    bytes.fromhex(parts[2])
    bytes.fromhex(parts[3])


def test_verify_password_accepts_correct_password() -> None:
    plain_password = "test123"

    password_hash = hash_password(plain_password)

    assert verify_password(plain_password, password_hash) is True


def test_verify_password_rejects_wrong_password() -> None:
    plain_password = "test123"

    password_hash = hash_password(plain_password)

    assert verify_password("wrong-password", password_hash) is False


def test_verify_password_rejects_changed_password_with_same_hash() -> None:
    password_hash = hash_password("test123")

    assert verify_password("test124", password_hash) is False


def test_hash_password_uses_different_salt_for_same_password() -> None:
    plain_password = "test123"

    first_hash = hash_password(plain_password)
    second_hash = hash_password(plain_password)

    assert first_hash != second_hash
    assert verify_password(plain_password, first_hash) is True
    assert verify_password(plain_password, second_hash) is True


@pytest.mark.parametrize(
    "stored_hash",
    [
        "",
        "not-a-hash",
        "pbkdf2_sha256$100000$bad-salt$bad-hash",
        "bcrypt$100000$001122$334455",
        "pbkdf2_sha256$not-number$001122$334455",
    ],
)
def test_verify_password_rejects_malformed_hashes(stored_hash: str) -> None:
    assert verify_password("test123", stored_hash) is False


def test_hash_password_supports_long_unicode_password() -> None:
    password = "lozinka-čćžšđ-" * 20

    password_hash = hash_password(password)

    assert verify_password(password, password_hash) is True
    assert verify_password(password + "x", password_hash) is False


def test_decode_access_token_returns_payload() -> None:
    token = create_access_token(
        subject="student@example.com",
        extra_claims={"role": "student"},
    )

    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "student@example.com"
    assert payload["role"] == "student"
    assert "exp" in payload


def test_decode_access_token_works_without_extra_claims() -> None:
    token = create_access_token(subject="student@example.com")

    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "student@example.com"
    assert "exp" in payload


def test_decode_access_token_rejects_invalid_token() -> None:
    payload = decode_access_token("not-a-real-token")

    assert payload is None
