"""PaymentExecutor: Razorpay test-mode adapter for Money actions.

Never constructs a live-key client. ChaosInjector, if provided, runs immediately
before the matching Razorpay SDK call. Capture is off by default.
"""

from __future__ import annotations

from typing import Any

from src.config import settings
from src.models.mandate import Mandate
from src.models.proposal import Proposal
from src.services.chaos import ChaosInjector


class PaymentExecutor:
    """Thin wrapper around razorpay.Client. TEST MODE only."""

    def __init__(
        self,
        client: Any | None = None,
        chaos: ChaosInjector | None = None,
        capture: bool = False,
    ) -> None:
        key_id = settings.RAZORPAY_KEY_ID
        if not str(key_id).startswith("rzp_test_"):
            raise RuntimeError("Razorpay TEST MODE only")
        if client is None:
            import razorpay

            client = razorpay.Client(auth=(key_id, settings.RAZORPAY_KEY_SECRET))
        self._client = client
        self._chaos = chaos
        self._capture = capture

    def create_order(
        self,
        amount: int,
        currency: str = "INR",
        receipt: str | None = None,
    ) -> dict[str, Any]:
        """Create a Razorpay order (amount in paise)."""
        if self._chaos is not None:
            self._chaos.inject_failure("razorpay_create_order")
        payload: dict[str, Any] = {"amount": amount, "currency": currency}
        if receipt is not None:
            payload["receipt"] = receipt
        return self._client.order.create(payload)

    def capture_payment(self, payment_id: str, amount: int) -> dict[str, Any]:
        """Capture a Razorpay payment (amount in paise)."""
        if self._chaos is not None:
            self._chaos.inject_failure("razorpay_capture_payment")
        return self._client.payment.capture(payment_id, amount)

    def execute(
        self,
        mandate: Mandate,
        proposal: Proposal,
        payment_id: str | None = None,
    ) -> dict[str, Any]:
        """Create an order for the Proposal. Capture only if enabled."""
        created = self.create_order(
            amount=proposal.quoted_total_paise,
            currency=mandate.currency,
            receipt=mandate.mandate_id,
        )
        if self._capture and payment_id:
            captured = self.capture_payment(payment_id, proposal.quoted_total_paise)
            return {"order": created, "capture": captured}
        return created
