from __future__ import annotations

from bukkystore_api.auth.security import hash_password, hash_token, new_token, verify_password


def test_password_hash_round_trip_uses_unique_salts() -> None:
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")

    assert first != second
    assert verify_password("correct horse battery staple", first) is True
    assert verify_password("incorrect password", first) is False


def test_malformed_password_hash_fails_securely() -> None:
    assert verify_password("anything", "not-a-supported-hash") is False
    assert verify_password("anything", "bcrypt$1$2$3$bad$bad") is False


def test_session_tokens_are_random_and_keyed() -> None:
    first = new_token()
    second = new_token()

    assert first != second
    assert len(first) >= 32
    assert hash_token(first, "secret-one") != hash_token(first, "secret-two")
