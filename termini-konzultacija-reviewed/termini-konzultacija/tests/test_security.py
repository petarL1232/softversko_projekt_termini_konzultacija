#Petar dio
import pytest

from app.services.security import hash_password, verify_password


def test_hash_password_does_not_return_plain_password() -> None:
    plain_password = "test123"

    password_hash = hash_password(plain_password)

    assert password_hash != plain_password
    assert password_hash.startswith("$2")


def test_verify_password_accepts_correct_password() -> None:
    plain_password = "test123"
    password_hash = hash_password(plain_password)

    assert verify_password(plain_password, password_hash) is True


def test_verify_password_rejects_wrong_password() -> None:
    password_hash = hash_password("test123")

    assert verify_password("wrong-password", password_hash) is False


def test_hash_password_rejects_too_long_password() -> None:
    too_long_password = "a" * 73

    with pytest.raises(ValueError):
        hash_password(too_long_password)
