"""Pydantic models for C2 Semantic Catalog.

Follows CONTEXT.md: Catalog is the agent-readable list of offers.
All amounts follow project convention (price in paise as int).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DiscountBounds(BaseModel):
    """Allowed discount range for an item (percent)."""

    min_percent: int = Field(ge=0, le=100)
    max_percent: int = Field(ge=0, le=100)


class CatalogItem(BaseModel):
    """A single offer from the merchant's Catalog."""

    sku: str
    name: str
    description: str = ""
    unit_amount_paise: int = Field(ge=0)
    inventory: int = Field(ge=0)
    discount_bounds: DiscountBounds
    categories: list[str] = Field(default_factory=list)


class CatalogResponse(BaseModel):
    """Response for a merchant's full catalog."""

    merchant_id: str
    merchant_name: str
    items: list[CatalogItem] = Field(default_factory=list)
    updated_at: str
