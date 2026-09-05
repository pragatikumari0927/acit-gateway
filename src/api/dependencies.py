"""FastAPI dependency injection for async DB sessions and services."""

from __future__ import annotations

import hmac
from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import settings
from src.db.core import get_session as _get_session
from src.services.audit import AuditLogger
from src.services.catalog import CatalogService
from src.services.chaos import ChaosInjector
from src.services.executor import PaymentExecutor
from src.services.firewall import PromptFirewall
from src.services.policy import PolicyEngine
from src.services.vault import Vault

_REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_ADMIN_SCOPE = "audit:admin"
_audit_admin_api_key = APIKeyHeader(
    name="X-API-Key",
    scheme_name="AuditAdminApiKey",
    description=(
        "Dedicated merchant/operator API key carrying the server-assigned "
        "`audit:admin` scope."
    ),
    auto_error=False,
)


def _db_path_from_url(url: str) -> str:
    """Convert a sqlite URL to a filesystem path suitable for aiosqlite."""
    prefix = "sqlite+aiosqlite:///"
    if url.startswith(prefix):
        return url[len(prefix):]
    prefix2 = "sqlite:///"
    if url.startswith(prefix2):
        return url[len(prefix2):]
    return url


def _default_catalog_file() -> str:
    """Resolve catalogs.json without introducing a new env var."""
    candidates = (
        _REPO_ROOT / "tests" / "fixtures" / "catalogs.json",
        _REPO_ROOT / "data" / "catalogs.json",
    )
    for path in candidates:
        if path.is_file():
            return str(path)
    return str(candidates[0])


@lru_cache
def get_engine() -> AsyncEngine:
    from src.db.core import make_engine

    return make_engine(_db_path_from_url(settings.DATABASE_URL))


async def get_session() -> AsyncIterator[AsyncSession]:
    async for session in _get_session(get_engine()):
        yield session


@lru_cache
def get_vault() -> Vault:
    """Mandate Vault keyed off DATABASE_URL. One instance per process."""
    return Vault(_db_path_from_url(settings.DATABASE_URL))


@lru_cache
def get_audit() -> AuditLogger:
    """Hash-chained Audit logger on the same SQLite file as Vault."""
    return AuditLogger(_db_path_from_url(settings.DATABASE_URL))


def require_audit_admin(
    api_key: str | None = Security(_audit_admin_api_key),
) -> None:
    """Authorize full Audit export for an operator with the audit-admin scope."""
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    is_audit_admin = hmac.compare_digest(api_key, settings.AUDIT_ADMIN_API_KEY)
    is_operator = hmac.compare_digest(api_key, settings.API_KEY)
    if not is_audit_admin and not is_operator:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    if not is_audit_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required scope: {AUDIT_ADMIN_SCOPE}",
        )


@lru_cache
def get_catalog() -> CatalogService:
    return CatalogService(_default_catalog_file())


@lru_cache
def get_firewall() -> PromptFirewall:
    return PromptFirewall()


@lru_cache
def get_chaos() -> ChaosInjector:
    return ChaosInjector(
        enabled=settings.CHAOS_ENABLED,
        failure_rate=settings.CHAOS_FAILURE_RATE,
    )


def get_policy(
    vault: Vault = Depends(get_vault),
    catalog: CatalogService = Depends(get_catalog),
) -> PolicyEngine:
    return PolicyEngine(vault, catalog)


@lru_cache
def get_razorpay_client() -> object:
    """Build the test-mode Razorpay adapter once. Never construct inside parser/policy/firewall."""
    key_id = settings.RAZORPAY_KEY_ID
    if not str(key_id).startswith("rzp_test_"):
        raise RuntimeError("Razorpay TEST MODE only")
    import razorpay

    return razorpay.Client(auth=(key_id, settings.RAZORPAY_KEY_SECRET))


def get_executor(
    chaos: ChaosInjector = Depends(get_chaos),
    client: object = Depends(get_razorpay_client),
) -> PaymentExecutor:
    return PaymentExecutor(client=client, chaos=chaos)
