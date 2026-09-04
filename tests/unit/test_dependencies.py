"""DI construction: cached Vault/Audit, injected Razorpay client."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.api import dependencies as deps
from src.services.chaos import ChaosInjector


def test_get_vault_and_audit_are_cached():
    deps.get_vault.cache_clear()
    deps.get_audit.cache_clear()
    try:
        assert deps.get_vault() is deps.get_vault()
        assert deps.get_audit() is deps.get_audit()
    finally:
        deps.get_vault.cache_clear()
        deps.get_audit.cache_clear()


def test_get_executor_uses_injected_client():
    client = MagicMock()
    chaos = ChaosInjector(enabled=False, failure_rate=0.0)
    executor = deps.get_executor(chaos=chaos, client=client)
    assert executor._client is client
