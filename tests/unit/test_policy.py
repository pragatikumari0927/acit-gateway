"""Unit tests for C5 PolicyEngine (TDD). Public seams only."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio

from src.models.mandate import Mandate, OrderItem, Protocol
from src.models.proposal import Proposal
from src.services.catalog import CatalogService
from src.services.vault import Vault

CATALOG_FILE = "tests/fixtures/catalogs.json"
SKU = "SKU-001"
UNIT_PAISE = 19900  # catalogs.json Widget
MAX_PERCENT = 15
# 19900 * 1 * 15 // 100
MAX_DISCOUNT_QTY1 = 2985


def _future() -> datetime:
    return datetime.now(UTC).replace(year=2035)


def _mandate(**kwargs) -> Mandate:
    defaults = {
        "mandate_id": "m-pol-1",
        "agent_id": "agent-pol-1",
        "protocol": Protocol.AP2,
        "max_amount_paise": 50_000,
        "sku_allowlist": [SKU, "SKU-002"],
        "expires_at": _future(),
    }
    defaults.update(kwargs)
    return Mandate(**defaults)


def _proposal(**kwargs) -> Proposal:
    defaults = {
        "mandate_id": "m-pol-1",
        "merchant_id": "m_test",
        "items": [OrderItem(sku=SKU, quantity=1, unit_amount_paise=UNIT_PAISE)],
        "quoted_total_paise": UNIT_PAISE,
        "quoted_discount_paise": 0,
        "copy": [],
    }
    defaults.update(kwargs)
    return Proposal(**defaults)


@pytest_asyncio.fixture
async def vault(tmp_path) -> Vault:
    v = Vault(tmp_path / "policy.db")
    await v.register_agent("agent-pol-1", "pub")
    await v.store_mandate(_mandate())
    return v


@pytest.fixture
def catalog() -> CatalogService:
    return CatalogService(CATALOG_FILE)


@pytest.mark.asyncio
async def test_evaluate_proposal_allows_in_bounds(vault, catalog):
    from src.services.policy import PolicyEngine

    engine = PolicyEngine(vault, catalog)
    result = await engine.evaluate_proposal(_proposal())
    assert result.allowed is True
    assert result.reason_code is None
    assert result.violations == []
    assert result.mandate_id == "m-pol-1"


@pytest.mark.asyncio
async def test_evaluate_proposal_mandate_invalid_when_unknown(vault, catalog):
    from src.services.policy import PolicyEngine

    engine = PolicyEngine(vault, catalog)
    result = await engine.evaluate_proposal(_proposal(mandate_id="no-such"))
    assert result.allowed is False
    assert result.reason_code == "mandate_invalid"
    assert "mandate_invalid" in result.violations


@pytest.mark.asyncio
async def test_evaluate_proposal_over_limit(vault, catalog):
    from src.services.policy import PolicyEngine

    engine = PolicyEngine(vault, catalog)
    result = await engine.evaluate_proposal(_proposal(quoted_total_paise=50_001))
    assert result.allowed is False
    assert result.reason_code == "over_limit"


@pytest.mark.asyncio
async def test_evaluate_proposal_sku_not_allowed(vault, catalog):
    from src.services.policy import PolicyEngine

    engine = PolicyEngine(vault, catalog)
    result = await engine.evaluate_proposal(
        _proposal(items=[OrderItem(sku="SKU-999", quantity=1, unit_amount_paise=100)])
    )
    assert result.allowed is False
    assert result.reason_code == "sku_not_allowed"


@pytest.mark.asyncio
async def test_evaluate_proposal_invented_price(vault, catalog):
    from src.services.policy import PolicyEngine

    engine = PolicyEngine(vault, catalog)
    result = await engine.evaluate_proposal(
        _proposal(items=[OrderItem(sku=SKU, quantity=1, unit_amount_paise=1)])
    )
    assert result.allowed is False
    assert result.reason_code == "invented_price"


@pytest.mark.asyncio
async def test_evaluate_proposal_invented_discount_over_percent(vault, catalog):
    from src.services.policy import PolicyEngine

    engine = PolicyEngine(vault, catalog)
    result = await engine.evaluate_proposal(
        _proposal(quoted_discount_paise=MAX_DISCOUNT_QTY1 + 1)
    )
    assert result.allowed is False
    assert result.reason_code == "invented_discount"


@pytest.mark.asyncio
async def test_evaluate_proposal_invented_discount_negative(vault, catalog):
    from src.services.policy import PolicyEngine

    engine = PolicyEngine(vault, catalog)
    bad = Proposal.model_construct(
        mandate_id="m-pol-1",
        merchant_id="m_test",
        items=[OrderItem(sku=SKU, quantity=1, unit_amount_paise=UNIT_PAISE)],
        quoted_total_paise=UNIT_PAISE,
        quoted_discount_paise=-1,
        copy=[],
    )
    result = await engine.evaluate_proposal(bad)
    assert result.allowed is False
    assert result.reason_code == "invented_discount"


@pytest.mark.asyncio
async def test_evaluate_proposal_allows_discount_at_percent_bound(vault, catalog):
    from src.services.policy import PolicyEngine

    engine = PolicyEngine(vault, catalog)
    result = await engine.evaluate_proposal(
        _proposal(quoted_discount_paise=MAX_DISCOUNT_QTY1)
    )
    assert result.allowed is True


@pytest.mark.asyncio
async def test_evaluate_proposal_dark_pattern_urgency(vault, catalog):
    from src.services.policy import PolicyEngine

    engine = PolicyEngine(vault, catalog)
    result = await engine.evaluate_proposal(_proposal(copy=["Act now — limited time"]))
    assert result.allowed is False
    assert result.reason_code == "dark_pattern"


@pytest.mark.asyncio
async def test_evaluate_proposal_dark_pattern_confirm_shaming(vault, catalog):
    from src.services.policy import PolicyEngine

    engine = PolicyEngine(vault, catalog)
    result = await engine.evaluate_proposal(
        _proposal(copy={"cta": "No thanks, I don't want to save"})
    )
    assert result.allowed is False
    assert result.reason_code == "dark_pattern"


@pytest.mark.asyncio
async def test_evaluate_proposal_first_failure_wins_over_limit_before_sku(vault, catalog):
    from src.services.policy import PolicyEngine

    engine = PolicyEngine(vault, catalog)
    result = await engine.evaluate_proposal(
        _proposal(
            quoted_total_paise=99_999,
            items=[OrderItem(sku="NOT-ALLOWED", quantity=1, unit_amount_paise=1)],
        )
    )
    assert result.reason_code == "over_limit"


@pytest.mark.asyncio
async def test_vault_get_mandate_roundtrip(tmp_path):
    v = Vault(tmp_path / "get-m.db")
    m = _mandate(mandate_id="m-get-1")
    await v.register_agent(m.agent_id, "pub")
    await v.store_mandate(m)
    loaded = await v.get_mandate("m-get-1")
    assert loaded is not None
    assert loaded.mandate_id == "m-get-1"
    assert loaded.max_amount_paise == m.max_amount_paise
    assert await v.get_mandate("missing") is None
