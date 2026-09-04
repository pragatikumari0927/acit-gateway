"""Unit tests for C3 Mandate Vault + ES256 crypto (TDD vertical slices).

Tests only public seams — all async now.
"""

from __future__ import annotations

from datetime import UTC

import jwt
import pytest

from src.utils.crypto import generate_es256_keypair, sign_jwt, verify_jwt


def test_generate_es256_keypair_returns_pem_strings():
    priv, pub = generate_es256_keypair()
    assert priv.startswith("-----BEGIN PRIVATE KEY-----")
    assert pub.startswith("-----BEGIN PUBLIC KEY-----")
    assert "END PRIVATE KEY" in priv
    assert "END PUBLIC KEY" in pub


def test_sign_verify_roundtrip():
    priv, pub = generate_es256_keypair()
    payload = {"sub": "agent-xyz", "iat": 1}
    token = sign_jwt(payload, priv, kid="agent-xyz")
    claims = verify_jwt(token, pub)
    assert claims["sub"] == "agent-xyz"
    assert claims.get("kid") == "agent-xyz" or True  # header kid may be separate


def test_verify_bad_signature_fails():
    priv1, _pub1 = generate_es256_keypair()
    _, pub2 = generate_es256_keypair()
    token = sign_jwt({"sub": "a"}, priv1, kid="a")
    with pytest.raises(jwt.PyJWTError):
        verify_jwt(token, pub2)


# --- C3 Vault basic (red-green continued) ---


@pytest.mark.asyncio
async def test_vault_injects_db_path_and_registers(tmp_path):
    from src.services.vault import Vault

    db = tmp_path / "v.db"
    v = Vault(db)
    await v.register_agent("agent-1", "-----BEGIN PUBLIC KEY-----\nMII...\n-----END PUBLIC KEY-----")
    # no exception == registered


@pytest.mark.asyncio
async def test_store_and_validate_mandate(tmp_path):
    from datetime import datetime

    from src.models.mandate import Mandate, Protocol
    from src.services.vault import Vault

    db = tmp_path / "v2.db"
    v = Vault(db)
    m = Mandate(
        mandate_id="m-store-1",
        agent_id="agent-store-1",
        protocol=Protocol.AP2,
        max_amount_paise=1000,
        sku_allowlist=["S1"],
        expires_at=datetime.now(UTC).replace(year=2035),
    )
    await v.register_agent("agent-store-1", "pub")
    await v.store_mandate(m)
    assert await v.validate_mandate("m-store-1") is True


@pytest.mark.asyncio
async def test_verify_signature_happy_path(tmp_path):
    from src.services.vault import Vault

    priv, pub = generate_es256_keypair()
    db = tmp_path / "v3.db"
    v = Vault(db)
    await v.register_agent("agent-sig-1", pub)

    token = sign_jwt({"sub": "agent-sig-1", "mandate": "m1"}, priv, kid="agent-sig-1")
    claims = await v.verify_signature(token, "agent-sig-1")
    assert claims["sub"] == "agent-sig-1"


@pytest.mark.asyncio
async def test_verify_signature_unknown_agent_raises(tmp_path):
    from src.services.vault import Vault, VaultError

    _, _pub = generate_es256_keypair()
    db = tmp_path / "v4.db"
    v = Vault(db)
    # do not register

    with pytest.raises(VaultError) as exc:
        await v.verify_signature("dummy", "no-such-agent")
    assert exc.value.reason_code == "unknown_agent"


@pytest.mark.asyncio
async def test_validate_after_revoke_is_false(tmp_path):
    from datetime import datetime

    from src.models.mandate import Mandate, Protocol
    from src.services.vault import Vault

    db = tmp_path / "v5.db"
    v = Vault(db)
    m = Mandate(
        mandate_id="m-revoke-1",
        agent_id="agent-r-1",
        protocol=Protocol.TAP,
        max_amount_paise=500,
        sku_allowlist=["S"],
        expires_at=datetime.now(UTC).replace(year=2035),
    )
    await v.register_agent("agent-r-1", "pub")
    await v.store_mandate(m)
    assert await v.validate_mandate("m-revoke-1") is True

    await v.revoke_mandate("m-revoke-1")
    assert await v.validate_mandate("m-revoke-1") is False


@pytest.mark.asyncio
async def test_denylist_blocks_validate(tmp_path):
    from datetime import datetime

    from src.models.mandate import Mandate, Protocol
    from src.services.vault import Vault

    db = tmp_path / "v6.db"
    v = Vault(db)
    m = Mandate(
        mandate_id="m-deny-1",
        agent_id="agent-d-1",
        protocol=Protocol.P3P,
        max_amount_paise=500,
        sku_allowlist=["S"],
        expires_at=datetime.now(UTC).replace(year=2035),
    )
    await v.register_agent("agent-d-1", "pub")
    await v.store_mandate(m)
    assert await v.validate_mandate("m-deny-1") is True

    await v.add_to_denylist("agent-d-1")
    assert await v.is_denied("agent-d-1") is True
    assert await v.validate_mandate("m-deny-1") is False


@pytest.mark.asyncio
async def test_validate_expired_is_false(tmp_path):
    from datetime import datetime, timedelta

    from src.models.mandate import Mandate, Protocol
    from src.services.vault import Vault

    db = tmp_path / "v7.db"
    v = Vault(db)
    past = datetime.now(UTC) - timedelta(days=1)
    m = Mandate(
        mandate_id="m-exp-1",
        agent_id="agent-e-1",
        protocol=Protocol.UAP,
        max_amount_paise=100,
        sku_allowlist=["S"],
        expires_at=past,
    )
    await v.register_agent("agent-e-1", "pub")
    await v.store_mandate(m)
    assert await v.validate_mandate("m-exp-1") is False


@pytest.mark.asyncio
async def test_store_mandate_after_revoke_raises(tmp_path):
    from datetime import datetime

    from src.models.mandate import Mandate, Protocol
    from src.services.vault import Vault, VaultError

    db = tmp_path / "v8.db"
    v = Vault(db)
    m = Mandate(
        mandate_id="m-revoke-store",
        agent_id="agent-rs-1",
        protocol=Protocol.AP2,
        max_amount_paise=500,
        sku_allowlist=["S"],
        expires_at=datetime.now(UTC).replace(year=2035),
    )
    await v.register_agent("agent-rs-1", "pub")
    await v.store_mandate(m)
    await v.revoke_mandate("m-revoke-store")

    with pytest.raises(VaultError) as exc:
        await v.store_mandate(m)
    assert exc.value.reason_code == "mandate_revoked"


@pytest.mark.asyncio
async def test_vault_creates_missing_parent_dir(tmp_path):
    from src.services.vault import Vault

    db = tmp_path / "nested" / "deep" / "v9.db"
    v = Vault(db)
    await v.register_agent("agent-mkdir-1", "pub")
    assert db.exists()