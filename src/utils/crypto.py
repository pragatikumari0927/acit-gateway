"""ES256 (EC P-256) JWT helpers for C3 Vault identity.

Public: generate_es256_keypair, sign_jwt, verify_jwt.
"""

from __future__ import annotations

from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def generate_es256_keypair() -> tuple[str, str]:
    """Return (private_pem, public_pem) as PEM strings."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return priv_pem, pub_pem


def sign_jwt(payload: dict[str, Any], private_pem: str, kid: str) -> str:
    """Sign payload as JWT with ES256. Includes kid in header."""
    private_key = serialization.load_pem_private_key(private_pem.encode("utf-8"), password=None)
    headers = {"kid": kid, "alg": "ES256"}
    # PyJWT will use the key's curve
    return jwt.encode(payload, private_key, algorithm="ES256", headers=headers)  # type: ignore[arg-type]


def verify_jwt(token: str, public_pem: str) -> dict[str, Any]:
    """Verify ES256 JWT and return claims. Raises on failure."""
    public_key = serialization.load_pem_public_key(public_pem.encode("utf-8"))
    # audience/issuer not required in Phase 1
    claims = jwt.decode(token, public_key, algorithms=["ES256"])  # type: ignore[arg-type]
    return claims
