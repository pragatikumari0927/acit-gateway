"""Proof: ChaosInjector at the Razorpay seam -> run_execute Refusal + audit + verify_chain."""

from __future__ import annotations

import random
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from src.models.mandate import Mandate, OrderItem, Protocol
from src.models.proposal import Proposal
from src.services.audit import AuditLogger
from src.services.catalog import CatalogService
from src.services.chaos import ChaosInjector
from src.services.checkout import run_execute
from src.services.executor import PaymentExecutor
from src.services.firewall import PromptFirewall
from src.services.policy import PolicyEngine
from src.services.vault import Vault

SKU = "SKU-001"
UNIT_PAISE = 19900


def _mandate() -> Mandate:
    return Mandate(
        mandate_id="m-co-1",
        agent_id="agent-co-1",
        protocol=Protocol.AP2,
        max_amount_paise=50_000,
        sku_allowlist=[SKU, "SKU-002"],
        expires_at=datetime.now(UTC).replace(year=2035),
    )


def _proposal() -> Proposal:
    return Proposal(
        mandate_id="m-co-1",
        merchant_id="m_test",
        items=[OrderItem(sku=SKU, quantity=1, unit_amount_paise=UNIT_PAISE)],
        quoted_total_paise=UNIT_PAISE,
        quoted_discount_paise=0,
        copy=[],
    )


@pytest.mark.asyncio
async def test_chaos_fault_is_executor_failure_refusal_with_verified_chain(tmp_path):
    db = tmp_path / "chaos-graceful.db"
    vault = Vault(db)
    audit = AuditLogger(db)
    catalog = CatalogService("tests/fixtures/catalogs.json")
    policy = PolicyEngine(vault, catalog)
    firewall = PromptFirewall()
    await vault.register_agent("agent-co-1", "pub")
    await vault.store_mandate(_mandate())

    chaos = ChaosInjector(enabled=True, failure_rate=1.0, rng=random.Random(0))
    executor = PaymentExecutor(client=MagicMock(), chaos=chaos)

    result = await run_execute(
        _proposal(),
        protocol=None,
        envelope=None,
        firewall=firewall,
        vault=vault,
        policy=policy,
        executor=executor,
        audit=audit,
    )

    assert result.allowed is False
    assert result.reason_code == "executor_failure"
    assert result.payment is None
    chain = await audit.get_chain("m-co-1")
    assert any(row.outcome == "refusal" for row in chain)
    assert await audit.verify_chain() is True
