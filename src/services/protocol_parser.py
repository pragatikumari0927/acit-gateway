"""Protocol parser for C1: turns raw Protocol envelopes into Mandate.

Public seam: parse_envelope(protocol, envelope) -> Mandate
Per-protocol: parse_ap2, parse_tap, parse_p3p, parse_uap (structure only).

Failures raise ProtocolParseError with .reason_code (string).
"""

from __future__ import annotations

from datetime import UTC, datetime

from src.models.mandate import Mandate, OrderItem, Protocol


class ProtocolParseError(Exception):
    """Raised when a Protocol envelope cannot be parsed to Mandate."""

    def __init__(self, reason_code: str, message: str | None = None) -> None:
        self.reason_code = reason_code
        super().__init__(message or reason_code)


def parse_envelope(protocol: str | Protocol, envelope: dict) -> Mandate:
    """Dispatch to the appropriate parser by protocol.

    protocol may be enum or string name.
    """
    if isinstance(protocol, str):
        try:
            proto = Protocol(protocol.lower())
        except ValueError:
            raise ProtocolParseError("unknown_protocol") from None
    else:
        proto = protocol

    if not isinstance(envelope, dict):
        raise ProtocolParseError("invalid_envelope")

    if proto == Protocol.AP2:
        return parse_ap2(envelope)
    if proto == Protocol.TAP:
        return parse_tap(envelope)
    if proto == Protocol.P3P:
        return parse_p3p(envelope)
    if proto == Protocol.UAP:
        return parse_uap(envelope)

    raise ProtocolParseError("unknown_protocol")


def parse_ap2(envelope: dict) -> Mandate:
    """AP2 envelope -> Mandate (structure only for Phase 1)."""
    # Minimal normalization for TDD; later phases can enrich.
    return _normalize_to_mandate(envelope, Protocol.AP2)


def parse_tap(envelope: dict) -> Mandate:
    return _normalize_to_mandate(envelope, Protocol.TAP)


def parse_p3p(envelope: dict) -> Mandate:
    return _normalize_to_mandate(envelope, Protocol.P3P)


def parse_uap(envelope: dict) -> Mandate:
    return _normalize_to_mandate(envelope, Protocol.UAP)


def _normalize_to_mandate(envelope: dict, protocol: Protocol) -> Mandate:
    """Best-effort extraction from common shapes. Tests drive required keys."""
    # Accept both flat and nested common keys seen in test envelopes.
    mid = envelope.get("mandate_id") or envelope.get("id") or envelope.get("mandate", {}).get("id")
    aid = envelope.get("agent_id") or envelope.get("agent", {}).get("id")
    max_amt = envelope.get("max_amount_paise") or envelope.get("maxAmount") or 0
    cur = envelope.get("currency", "INR")
    skus = envelope.get("sku_allowlist") or envelope.get("skus") or []
    exp = envelope.get("expires_at") or envelope.get("expiresAt")
    itms = envelope.get("items") or []

    if not mid or not aid:
        raise ProtocolParseError("missing_required_field")

    if exp is None:
        raise ProtocolParseError("missing_expires_at")

    # Coerce expires if str (accept Z or offset)
    if isinstance(exp, str):
        s = exp.rstrip("Z")
        if exp.endswith("Z"):
            s += "+00:00"
        exp = datetime.fromisoformat(s)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)

    # Build items
    items = []
    for raw in itms:
        items.append(
            OrderItem(
                sku=raw.get("sku", ""),
                quantity=raw.get("quantity", 1),
                unit_amount_paise=raw.get("unit_amount_paise", 0),
                name=raw.get("name"),
            )
        )

    return Mandate(
        mandate_id=str(mid),
        agent_id=str(aid),
        protocol=protocol,
        max_amount_paise=int(max_amt),
        currency=str(cur),
        sku_allowlist=list(skus) if skus else [],
        expires_at=exp or datetime.now(UTC),
        items=items,
    )
