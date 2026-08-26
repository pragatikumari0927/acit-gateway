"""Crypto seam: ES256 JWT round-trip."""

import pytest

from src.utils.crypto import InvalidToken, generate_es256_keypair, sign_jwt, verify_jwt


def test_sign_and_verify_returns_payload() -> None:
    private_pem, public_pem = generate_es256_keypair()
    token = sign_jwt({"sub": "agent_01", "n": 1}, private_pem, kid="agent_01")
    claims = verify_jwt(token, public_pem)
    assert claims["sub"] == "agent_01"
    assert claims["n"] == 1


def test_wrong_key_is_invalid_token() -> None:
    private_pem, _ = generate_es256_keypair()
    _, other_public = generate_es256_keypair()
    token = sign_jwt({"sub": "agent_01"}, private_pem)
    with pytest.raises(InvalidToken) as exc:
        verify_jwt(token, other_public)
    assert exc.value.reason_code == "invalid_signature"


def test_tampered_token_is_invalid_token() -> None:
    private_pem, public_pem = generate_es256_keypair()
    token = sign_jwt({"sub": "agent_01"}, private_pem)
    parts = token.split(".")
    tampered = parts[0] + "." + parts[1] + "x." + parts[2]
    with pytest.raises(InvalidToken) as exc:
        verify_jwt(tampered, public_pem)
    assert exc.value.reason_code == "invalid_signature"
