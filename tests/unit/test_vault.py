"""Vault seam: identity, stored Mandates, denylist."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.models.mandate import Mandate, OrderItem, Protocol
from src.services.vault import Vault, VaultError
from src.utils.crypto import generate_es256_keypair


def _vault(tmp_path: Path) -> Vault:
    return Vault(tmp_path / "vault.db")


def _mandate(*, expires_at: datetime | None = None, mandate_id: str = "man_01") -> Mandate:
    when = expires_at or (datetime.now(timezone.utc) + timedelta(hours=1))
    return Mandate(
        mandate_id=mandate_id,
        agent_id="agent_01",
        protocol=Protocol.AP2,
        max_amount_paise=50000,
        currency="INR",
        sku_allowlist=["sku_tea"],
        expires_at=when,
        items=[OrderItem(sku="sku_tea", quantity=1, unit_amount_paise=10000)],
    )


def test_register_sign_and_verify_signature_rebuilds_mandate(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    private_pem, public_pem = generate_es256_keypair()
    vault.register_agent("agent_01", public_pem)
    mandate = _mandate()
    token = vault.sign_mandate(mandate, private_pem)
    verified = vault.verify_signature(token)
    assert verified.agent_id == "agent_01"
    assert verified.max_amount_paise == 50000
    assert verified.sku_allowlist == ["sku_tea"]
    assert verified.mandate_id == "man_01"


def test_wrong_key_verify_signature_fails(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    _, public_pem = generate_es256_keypair()
    other_private, _ = generate_es256_keypair()
    vault.register_agent("agent_01", public_pem)
    token = vault.sign_mandate(_mandate(), other_private)
    with pytest.raises(VaultError) as exc:
        vault.verify_signature(token)
    assert exc.value.reason_code == "invalid_signature"


def test_unknown_agent_signature_fails(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    private_pem, _ = generate_es256_keypair()
    token = vault.sign_mandate(_mandate(), private_pem)
    with pytest.raises(VaultError) as exc:
        vault.verify_signature(token)
    assert exc.value.reason_code == "unknown_agent"


def test_validate_expired_mandate_fails(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    _, public_pem = generate_es256_keypair()
    vault.register_agent("agent_01", public_pem)
    mandate = _mandate(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
    vault.store_mandate(mandate)
    with pytest.raises(VaultError) as exc:
        vault.validate_mandate(mandate)
    assert exc.value.reason_code == "expired"


def test_revoke_then_validate_fails(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    _, public_pem = generate_es256_keypair()
    vault.register_agent("agent_01", public_pem)
    mandate = _mandate()
    vault.store_mandate(mandate)
    vault.revoke_mandate(mandate.mandate_id)
    with pytest.raises(VaultError) as exc:
        vault.validate_mandate(mandate)
    assert exc.value.reason_code == "revoked"


def test_denylist_blocks_validate(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    _, public_pem = generate_es256_keypair()
    vault.register_agent("agent_01", public_pem)
    mandate = _mandate()
    vault.store_mandate(mandate)
    vault.add_to_denylist("agent_01", "compromised")
    assert vault.is_denied("agent_01") is True
    with pytest.raises(VaultError) as exc:
        vault.validate_mandate(mandate)
    assert exc.value.reason_code == "denied"


def test_validate_unstored_mandate_fails(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    _, public_pem = generate_es256_keypair()
    vault.register_agent("agent_01", public_pem)
    with pytest.raises(VaultError) as exc:
        vault.validate_mandate(_mandate())
    assert exc.value.reason_code == "unknown_mandate"


def test_duplicate_register_fails(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    _, public_pem = generate_es256_keypair()
    vault.register_agent("agent_01", public_pem)
    with pytest.raises(VaultError) as exc:
        vault.register_agent("agent_01", public_pem)
    assert exc.value.reason_code == "duplicate_agent"


def test_validate_active_mandate_returns_it(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    _, public_pem = generate_es256_keypair()
    vault.register_agent("agent_01", public_pem)
    mandate = _mandate()
    vault.store_mandate(mandate)
    assert vault.validate_mandate(mandate).mandate_id == "man_01"


def test_is_denied_false_when_not_listed(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    assert vault.is_denied("agent_01") is False
