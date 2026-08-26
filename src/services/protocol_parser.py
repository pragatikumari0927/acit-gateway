"""Parse a Protocol envelope into the canonical Mandate."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import NAMESPACE_URL, uuid5

from src.models.mandate import Mandate, OrderItem, Protocol

AP2_CHECKOUT_OPEN_VCT = "mandate.checkout.open.1"


class ProtocolParseError(Exception):
    """Structural Refusal of a Protocol envelope."""

    def __init__(self, reason_code: str, message: str | None = None) -> None:
        self.reason_code = reason_code
        super().__init__(message or reason_code)


def parse_envelope(protocol: Protocol, envelope: Mapping[str, Any]) -> Mandate:
    """Dispatch on Protocol and return a Mandate."""
    parsers = {
        Protocol.AP2: parse_ap2,
        Protocol.P3P: parse_p3p,
        Protocol.TAP: parse_tap,
        Protocol.UAP: parse_uap,
    }
    try:
        parse = parsers[protocol]
    except KeyError as exc:
        raise ProtocolParseError("unknown_protocol") from exc
    return parse(envelope)


def parse_ap2(envelope: Mapping[str, Any]) -> Mandate:
    """AP2-shaped open Checkout Mandate (not a full SD-JWT)."""
    vct = envelope.get("vct")
    if vct != AP2_CHECKOUT_OPEN_VCT:
        raise ProtocolParseError("unknown_vct")
    agent_id = _agent_id(envelope.get("sub") or (envelope.get("cnf") or {}).get("kid"))
    constraints = envelope.get("constraints") or {}
    max_amount = constraints.get("max_amount") or {}
    return _build(
        protocol=Protocol.AP2,
        envelope=envelope,
        agent_id=agent_id,
        max_amount_paise=_paise(max_amount.get("value")),
        currency=_currency(max_amount.get("currency")),
        sku_allowlist=_sku_allowlist(constraints.get("sku_allowlist")),
        expires_at=_expires(envelope.get("exp")),
        items=_items(envelope.get("items")),
        user_id=_optional_str(envelope.get("user_id")),
    )


def parse_p3p(envelope: Mapping[str, Any]) -> Mandate:
    """P3P-shaped delegated authorization (not HTTP 402)."""
    auth = envelope.get("authorization") or {}
    order = envelope.get("order") or {}
    return _build(
        protocol=Protocol.P3P,
        envelope=envelope,
        agent_id=_agent_id(envelope.get("agent_id")),
        max_amount_paise=_paise(auth.get("max_txn_paise")),
        currency=_currency(auth.get("currency")),
        sku_allowlist=_sku_allowlist(auth.get("skus")),
        expires_at=_expires(auth.get("exp")),
        items=_items(order.get("items")),
        user_id=_optional_str(envelope.get("user_id")),
    )


def parse_tap(envelope: Mapping[str, Any]) -> Mandate:
    """Project TAP envelope → Mandate. Acronym not expanded."""
    return _parse_flat(Protocol.TAP, envelope)


def parse_uap(envelope: Mapping[str, Any]) -> Mandate:
    """Project UAP envelope → Mandate (NPCI protocol is not a public spec)."""
    return _parse_flat(Protocol.UAP, envelope)


def _parse_flat(protocol: Protocol, envelope: Mapping[str, Any]) -> Mandate:
    return _build(
        protocol=protocol,
        envelope=envelope,
        agent_id=_agent_id(envelope.get("agent_id")),
        max_amount_paise=_paise(envelope.get("max_amount_paise")),
        currency=_currency(envelope.get("currency")),
        sku_allowlist=_sku_allowlist(envelope.get("sku_allowlist")),
        expires_at=_expires(envelope.get("exp")),
        items=_items(envelope.get("items")),
        user_id=_optional_str(envelope.get("user_id")),
    )


def _build(
    *,
    protocol: Protocol,
    envelope: Mapping[str, Any],
    agent_id: str,
    max_amount_paise: int,
    currency: str,
    sku_allowlist: list[str],
    expires_at: datetime,
    items: list[OrderItem],
    user_id: str | None,
) -> Mandate:
    return Mandate(
        mandate_id=_mandate_id(protocol, envelope),
        agent_id=agent_id,
        user_id=user_id,
        protocol=protocol,
        max_amount_paise=max_amount_paise,
        currency=currency,
        sku_allowlist=sku_allowlist,
        expires_at=expires_at,
        items=items,
    )


def _mandate_id(protocol: Protocol, envelope: Mapping[str, Any]) -> str:
    canonical = json.dumps(dict(envelope), sort_keys=True, separators=(",", ":"), default=str)
    return uuid5(NAMESPACE_URL, f"{protocol.value}:{canonical}").hex


def _agent_id(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProtocolParseError("missing_agent_id")
    return value.strip()


def _optional_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _paise(value: Any) -> int:
    if value is None or value == "":
        raise ProtocolParseError("invalid_amount")
    try:
        amount = int(value)
    except (TypeError, ValueError) as exc:
        raise ProtocolParseError("invalid_amount") from exc
    if amount < 0:
        raise ProtocolParseError("invalid_amount")
    return amount


def _currency(value: Any) -> str:
    if not value:
        return "INR"
    return str(value)


def _sku_allowlist(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ProtocolParseError("empty_sku_allowlist")
    skus = [str(sku) for sku in value if str(sku).strip()]
    if not skus:
        raise ProtocolParseError("empty_sku_allowlist")
    return skus


def _expires(value: Any) -> datetime:
    if value is None or value == "":
        raise ProtocolParseError("missing_exp")
    try:
        ts = int(value)
    except (TypeError, ValueError) as exc:
        raise ProtocolParseError("missing_exp") from exc
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _items(value: Any) -> list[OrderItem]:
    if not value:
        return []
    if not isinstance(value, list):
        raise ProtocolParseError("invalid_amount")
    items: list[OrderItem] = []
    for raw in value:
        try:
            quantity = int(raw["quantity"])
            unit_amount_paise = int(raw["unit_amount_paise"])
            sku = str(raw["sku"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ProtocolParseError("invalid_amount") from exc
        if quantity <= 0 or unit_amount_paise < 0:
            raise ProtocolParseError("invalid_amount")
        items.append(
            OrderItem(
                sku=sku,
                quantity=quantity,
                unit_amount_paise=unit_amount_paise,
                name=_optional_str(raw.get("name")),
            )
        )
    return items
