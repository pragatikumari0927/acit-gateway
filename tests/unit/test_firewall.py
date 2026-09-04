"""Unit tests for C4 Prompt Firewall (TDD vertical slices).

Clean → safe. Poisoned (IDPI) → blocked + reason.
"""

from __future__ import annotations

import json
import logging

import pytest

from src.services.firewall import PromptFirewall


def _load(name: str) -> dict:
    path = f"tests/fixtures/idpi_payloads.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data[name]


def test_firewall_sanitize_clean_returns_true_and_payload():
    fw = PromptFirewall()
    payload = _load("clean")
    ok, cleaned, reason = fw.sanitize(payload)
    assert ok is True
    assert reason is None
    assert isinstance(cleaned, dict)
    assert cleaned["protocol"] == "ap2"


def test_firewall_detects_html_comment():
    fw = PromptFirewall()
    payload = _load("poison_html_comment")
    ok, cleaned, reason = fw.sanitize(payload)
    assert ok is False
    assert cleaned is None
    assert reason == "idpi_detected"


def test_firewall_detects_instruction_override():
    fw = PromptFirewall()
    payload = _load("poison_instruction_override")
    ok, cleaned, reason = fw.sanitize(payload)
    assert ok is False
    assert cleaned is None
    assert reason == "idpi_detected"


def test_firewall_detects_zero_width():
    fw = PromptFirewall()
    payload = _load("poison_zero_width")
    ok, cleaned, reason = fw.sanitize(payload)
    assert ok is False
    assert cleaned is None
    assert reason == "idpi_detected"


def test_firewall_allows_soft_hyphen_in_product_text():
    fw = PromptFirewall()
    payload = _load("clean_soft_hyphen")
    ok, cleaned, reason = fw.sanitize(payload)
    assert ok is True
    assert reason is None
    assert "\u00ad" not in cleaned["envelope"]["desc"]


def test_firewall_detects_soft_hyphen_split_phrase():
    fw = PromptFirewall()
    payload = _load("poison_soft_hyphen_split")
    ok, cleaned, reason = fw.sanitize(payload)
    assert ok is False
    assert cleaned is None
    assert reason == "idpi_detected"


def test_firewall_detects_bad_key_and_nested():
    fw = PromptFirewall()
    payload = _load("poison_nested")
    ok, cleaned, reason = fw.sanitize(payload)
    assert ok is False
    assert cleaned is None
    assert reason == "idpi_detected"


def test_firewall_blocks_and_logs(caplog):
    fw = PromptFirewall()
    payload = _load("poison_html_comment")
    with caplog.at_level(logging.WARNING):
        ok, _, reason = fw.sanitize(payload)
    assert ok is False
    assert reason == "idpi_detected"
    assert any("idpi" in r.message.lower() or "idpi_detected" in r.message for r in caplog.records)
