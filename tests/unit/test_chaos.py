"""Unit tests for C7 ChaosInjector. Public seams; injected RNG."""

from __future__ import annotations

import random

import pytest

from src.services.chaos import ChaosInjector


def test_disabled_never_fails():
    rng = random.Random(0)
    chaos = ChaosInjector(enabled=False, failure_rate=1.0, rng=rng)
    assert chaos.should_fail() is False
    chaos.inject_failure("razorpay_create_order")  # must not raise


def test_enabled_rate_zero_never_fails():
    rng = random.Random(1)
    chaos = ChaosInjector(enabled=True, failure_rate=0.0, rng=rng)
    for _ in range(20):
        assert chaos.should_fail() is False
    chaos.inject_failure("razorpay_create_order")


def test_enabled_rate_one_fails_create():
    rng = random.Random(2)
    chaos = ChaosInjector(enabled=True, failure_rate=1.0, rng=rng)
    assert chaos.should_fail() is True
    with pytest.raises(TimeoutError):
        chaos.inject_failure("razorpay_create_order")


def test_enabled_rate_one_fails_capture():
    rng = random.Random(3)
    chaos = ChaosInjector(enabled=True, failure_rate=1.0, rng=rng)
    with pytest.raises((TimeoutError, Exception)):
        chaos.inject_failure("razorpay_capture_payment")


def test_unknown_api_call_never_raises():
    rng = random.Random(4)
    chaos = ChaosInjector(enabled=True, failure_rate=1.0, rng=rng)
    chaos.inject_failure("vault_store")  # not a Razorpay seam


def test_should_fail_uses_injected_rng():
    always = random.Random(0)

    class _AlwaysLow:
        def random(self) -> float:
            return 0.0

    chaos = ChaosInjector(enabled=True, failure_rate=0.5, rng=_AlwaysLow())  # type: ignore[arg-type]
    assert chaos.should_fail() is True
    del always
