"""Proposal and PolicyResult for C5 Guardrails evaluation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.models.mandate import OrderItem

CopyText = str | list[str] | dict[str, str]


class Proposal(BaseModel):
    """What the Agent wants to buy now, inside an existing Mandate.

    `merchant_id` is required so Catalog lookups can be keyed the same way as
    CatalogService.get_item. It is not a DB column.
    """

    mandate_id: str
    merchant_id: str
    items: list[OrderItem]
    quoted_total_paise: int = Field(ge=0)
    quoted_discount_paise: int = Field(default=0)
    copy: CopyText = Field(default_factory=list)


class PolicyResult(BaseModel):
    """C5 outcome. `allowed=True` is the only green light for a Money action."""

    mandate_id: str
    allowed: bool
    reason_code: str | None = None
    violations: list[str] = Field(default_factory=list)


class CheckoutExecuteResult(PolicyResult):
    """Money-action outcome. Refusal and allow share the PolicyResult interface."""

    payment: dict[str, Any] | None = None
