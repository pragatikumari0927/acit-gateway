"""Canonical Mandate: the Gateway's only internal spend envelope."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Protocol(str, Enum):
    """Inbound Protocol envelope family."""

    AP2 = "ap2"
    TAP = "tap"
    P3P = "p3p"
    UAP = "uap"


class OrderItem(BaseModel):
    """A line the Agent is authorised to buy, in paise."""

    sku: str
    quantity: int = Field(gt=0)
    unit_amount_paise: int = Field(ge=0)
    name: str | None = None


class Mandate(BaseModel):
    """User-authorised spend envelope: amount, SKU allow-list, TTL, Agent identity."""

    mandate_id: str
    agent_id: str
    user_id: str | None = None
    protocol: Protocol
    max_amount_paise: int = Field(ge=0)
    currency: str = "INR"
    sku_allowlist: list[str] = Field(min_length=1)
    expires_at: datetime
    items: list[OrderItem] = Field(default_factory=list)


InternalMandate = Mandate
