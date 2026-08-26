"""ES256 JWT helpers for Agent identity. Deterministic — no LLM."""

from __future__ import annotations

from typing import Any, Mapping

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from jwt import InvalidTokenError as PyJWTInvalidTokenError


class InvalidToken(Exception):
    """JWT failed verification."""

    def __init__(self, reason_code: str = "invalid_signature", message: str | None = None) -> None:
        self.reason_code = reason_code
        super().__init__(message or reason_code)


def generate_es256_keypair() -> tuple[str, str]:
    """Return (private_pem, public_pem) for ES256."""
    key = ec.generate_private_key(ec.SECP256R1())
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


def sign_jwt(payload: Mapping[str, Any], private_pem: str, *, kid: str | None = None) -> str:
    """Sign `payload` with ES256. `kid` is written to the JWT header when set."""
    headers = {"kid": kid} if kid else None
    return jwt.encode(dict(payload), private_pem, algorithm="ES256", headers=headers)


def verify_jwt(token: str, public_pem: str) -> dict[str, Any]:
    """Verify an ES256 JWT and return claims."""
    try:
        claims = jwt.decode(token, public_pem, algorithms=["ES256"])
    except PyJWTInvalidTokenError as exc:
        raise InvalidToken("invalid_signature") from exc
    if not isinstance(claims, dict):
        raise InvalidToken("invalid_signature")
    return claims


def unverified_header(token: str) -> dict[str, Any]:
    """Read JWT header without verifying the signature (to look up `kid`)."""
    try:
        header = jwt.get_unverified_header(token)
    except PyJWTInvalidTokenError as exc:
        raise InvalidToken("invalid_signature") from exc
    return header
