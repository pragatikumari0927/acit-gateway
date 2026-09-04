"""ChaosInjector (C7): failure injection at the Razorpay adapter only.

Deterministic when an rng is injected. Never fails when disabled.
"""

from __future__ import annotations

import random

_RAZORPAY_CALLS = frozenset({"razorpay_create_order", "razorpay_capture_payment"})


class ChaosInjector:
    """Inject timeouts / Razorpay-like errors into Money-action seams."""

    def __init__(
        self,
        enabled: bool,
        failure_rate: float,
        rng: random.Random | None = None,
    ) -> None:
        self.enabled = enabled
        self.failure_rate = failure_rate
        self._rng = rng if rng is not None else random.Random()

    def should_fail(self) -> bool:
        """Return True when a fault should be injected for the next call."""
        if not self.enabled:
            return False
        return self._rng.random() < self.failure_rate

    def inject_failure(self, api_call: str) -> None:
        """Raise TimeoutError for Razorpay create/capture when should_fail.

        Unknown `api_call` names are ignored. Disabled injectors never raise.
        """
        if api_call not in _RAZORPAY_CALLS:
            return
        if not self.should_fail():
            return
        raise TimeoutError(f"chaos injected for {api_call}")
