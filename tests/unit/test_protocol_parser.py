"""Parser seam: Protocol envelope → Mandate."""

from datetime import datetime, timezone

import pytest

from src.models.mandate import Protocol
from src.services.protocol_parser import ProtocolParseError, parse_ap2, parse_envelope, parse_p3p, parse_tap, parse_uap
from tests.fixtures.envelopes import AP2_VALID, P3P_VALID, TAP_VALID, UAP_VALID

EXPIRES = datetime(2030, 1, 1, tzinfo=timezone.utc)


def _assert_tea_mandate(mandate, protocol: Protocol) -> None:
    assert mandate.agent_id == "agent_01"
    assert mandate.protocol == protocol
    assert mandate.max_amount_paise == 50000
    assert mandate.currency == "INR"
    assert mandate.sku_allowlist == ["sku_tea"]
    assert mandate.expires_at == EXPIRES
    assert mandate.items[0].sku == "sku_tea"
    assert mandate.items[0].quantity == 1
    assert mandate.items[0].unit_amount_paise == 10000


def test_parse_ap2_valid_envelope_becomes_mandate() -> None:
    _assert_tea_mandate(parse_ap2(AP2_VALID), Protocol.AP2)


def test_parse_p3p_valid_envelope_becomes_mandate() -> None:
    _assert_tea_mandate(parse_p3p(P3P_VALID), Protocol.P3P)


def test_parse_tap_valid_envelope_becomes_mandate() -> None:
    _assert_tea_mandate(parse_tap(TAP_VALID), Protocol.TAP)


def test_parse_uap_valid_envelope_becomes_mandate() -> None:
    mandate = parse_uap(UAP_VALID)
    _assert_tea_mandate(mandate, Protocol.UAP)
    assert mandate.user_id == "user_01"


def test_parse_envelope_ap2_matches_parse_ap2() -> None:
    assert parse_envelope(Protocol.AP2, AP2_VALID) == parse_ap2(AP2_VALID)


def test_same_ap2_envelope_yields_stable_mandate_id() -> None:
    assert parse_ap2(AP2_VALID).mandate_id == parse_ap2(AP2_VALID).mandate_id


@pytest.mark.parametrize(
    ("parser", "envelope"),
    [
        (parse_ap2, {**AP2_VALID, "sub": None, "cnf": {}}),
        (parse_p3p, {**P3P_VALID, "agent_id": ""}),
        (parse_tap, {k: v for k, v in TAP_VALID.items() if k != "agent_id"}),
        (parse_uap, {k: v for k, v in UAP_VALID.items() if k != "agent_id"}),
    ],
)
def test_missing_agent_identity_is_parse_error(parser, envelope) -> None:
    with pytest.raises(ProtocolParseError) as exc:
        parser(envelope)
    assert exc.value.reason_code == "missing_agent_id"


def test_ap2_unknown_vct_is_parse_error() -> None:
    with pytest.raises(ProtocolParseError) as exc:
        parse_ap2({**AP2_VALID, "vct": "mandate.payment.1"})
    assert exc.value.reason_code == "unknown_vct"


def test_negative_amount_is_parse_error() -> None:
    with pytest.raises(ProtocolParseError) as exc:
        parse_p3p(
            {
                **P3P_VALID,
                "authorization": {**P3P_VALID["authorization"], "max_txn_paise": -1},
            }
        )
    assert exc.value.reason_code == "invalid_amount"


def test_empty_sku_allowlist_is_parse_error() -> None:
    with pytest.raises(ProtocolParseError) as exc:
        parse_tap({**TAP_VALID, "sku_allowlist": []})
    assert exc.value.reason_code == "empty_sku_allowlist"
