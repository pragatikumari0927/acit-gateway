---
name: chaos-testing
description: Chaos engineering, graceful degradation, failure injection for the gateway (Razorpay test-mode only). Use for resilience, error handling, and "what breaks at 2 AM" scenarios.
---

# Chaos Testing

For this project (Razorpay test-mode only, track 02 defense):

## Principles
- Inject failures only in test-mode adapters / mocks.
- Never touch real money flows.
- Test: network blips, slow responses, invalid signatures, rate limits, denylist hits, mandate expiry edge cases.
- Measure that the system returns proper Refusals + Audit events.

## Patterns
- Use pytest fixtures to patch the Razorpay client with chaos (random 5xx, timeouts, bad JSON).
- Test Vault denylist, signature verification under failure.
- Ensure HTTP layer (when added) returns correct refusal codes.
- Verify audit chain still appends even on failure paths.

## Example Harness (in tests)
```python
import pytest
from unittest.mock import patch

@pytest.mark.chaos
async def test_razorpay_timeout_refusal(chaos_client):
    with patch(...) as mock:
        mock.side_effect = TimeoutError
        resp = await call_money_action(...)
        assert resp.refused
        assert "timeout" in audit_event.reason
```

Combine with `tdd-test-engineer` + `security-audit`.
See superpowers verification-before-completion.
