"""FastAPI dependency injection for async DB sessions and services."""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path

from fastapi import Depends
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


def get_vault() -> Vault:
    """Mandate Vault keyed off DATABASE_URL."""
    return Vault(_db_path_from_url(settings.DATABASE_URL))


def get_audit() -> AuditLogger:
    """Hash-chained Audit logger on the same SQLite file as Vault."""
    return AuditLogger(_db_path_from_url(settings.DATABASE_URL))


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


def get_executor(chaos: ChaosInjector = Depends(get_chaos)) -> PaymentExecutor:
    return PaymentExecutor(chaos=chaos)
