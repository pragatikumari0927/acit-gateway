"""PolicyEngine (C5): deterministic Guardrails. No LLM.

First failure wins. Public seam: evaluate_proposal(proposal) -> PolicyResult.
"""

from __future__ import annotations

from src.models.proposal import PolicyResult, Proposal
from src.services.catalog import CatalogService
from src.services.vault import Vault

# Lowercase substrings for false urgency and confirm-shaming (C8).
_DARK_PATTERNS: tuple[str, ...] = (
    "limited time",
    "hurry",
    "act now",
    "only a few left",
    "last chance",
    "expires soon",
    "selling fast",
    "don't want to save",
    "i don't want to save",
    "no thanks, i don't",
    "i like paying more",
    "i prefer to pay full",
)


def _copy_haystack(copy: str | list[str] | dict[str, str]) -> str:
    if isinstance(copy, str):
        return copy.lower()
    if isinstance(copy, dict):
        return " ".join(str(v) for v in copy.values()).lower()
    return " ".join(str(v) for v in copy).lower()


def _refuse(mandate_id: str, reason_code: str) -> PolicyResult:
    return PolicyResult(
        mandate_id=mandate_id,
        allowed=False,
        reason_code=reason_code,
        violations=[reason_code],
    )


class PolicyEngine:
    """Deterministic policy / Guardrails. Vault + Catalog injected."""

    def __init__(self, vault: Vault, catalog: CatalogService) -> None:
        self.vault = vault
        self.catalog = catalog

    async def evaluate_proposal(self, proposal: Proposal) -> PolicyResult:
        """Evaluate a Proposal against Mandate bounds, Catalog, and Guardrails."""
        mandate_id = proposal.mandate_id
        if not await self.vault.validate_mandate(mandate_id):
            return _refuse(mandate_id, "mandate_invalid")

        mandate = await self.vault.get_mandate(mandate_id)
        if mandate is None:
            return _refuse(mandate_id, "mandate_invalid")

        if proposal.quoted_total_paise > mandate.max_amount_paise:
            return _refuse(mandate_id, "over_limit")

        allowlist = set(mandate.sku_allowlist)
        for line in proposal.items:
            if line.sku not in allowlist:
                return _refuse(mandate_id, "sku_not_allowed")

        max_discount = 0
        for line in proposal.items:
            try:
                offer = self.catalog.get_item(proposal.merchant_id, line.sku)
            except KeyError:
                return _refuse(mandate_id, "invented_price")
            if line.unit_amount_paise != offer.unit_amount_paise:
                return _refuse(mandate_id, "invented_price")
            max_discount += (
                offer.unit_amount_paise
                * line.quantity
                * offer.discount_bounds.max_percent
                // 100
            )

        if proposal.quoted_discount_paise < 0 or proposal.quoted_discount_paise > max_discount:
            return _refuse(mandate_id, "invented_discount")

        hay = _copy_haystack(proposal.copy)
        if any(p in hay for p in _DARK_PATTERNS):
            return _refuse(mandate_id, "dark_pattern")

        return PolicyResult(
            mandate_id=mandate_id,
            allowed=True,
            reason_code=None,
            violations=[],
        )
