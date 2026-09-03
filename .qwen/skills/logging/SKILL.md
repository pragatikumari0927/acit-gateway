---
name: logging
description: Structured logging, request correlation, error context, and safe log practices for FastAPI + SQLite services. No secrets in logs.
---

# Logging

## Principles for ACIT Gateway
- Structured logs (use `logging` + extra dicts or structlog if added).
- Include correlation id (request id) for tracing a Mandate through Parser → Vault → Firewall → action → Audit.
- Never log: private keys, full JWTs, raw PII from IDPI, full envelopes on error paths.
- Log at appropriate levels: INFO for high level decisions (allow/refuse), DEBUG for internal, WARNING/ERROR for failures that produce Refusals.
- Test-mode only: chaos logs are expected.

## FastAPI integration
- Use middleware or dependency for request logging + timing.
- Log key events with context: agent_id (sanitized), mandate_id (short), reason_code, duration.
- On Refusal paths always log the reason_code + minimal context for audit correlation.

## Example
```python
import logging
logger = logging.getLogger("acit.gateway")
logger.info("mandate.validated", extra={"agent_id": "...", "ttl_ok": True})
```

## With other skills
Combine with `error-handling`, `security-audit`, `chaos-testing`, `python-expert`.

See also production-readiness for log aggregation and retention.
