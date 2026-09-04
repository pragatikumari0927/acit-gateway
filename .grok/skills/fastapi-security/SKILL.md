---
name: fastapi-security
description: "FastAPI security patterns: auth, JWT validation, input sanitization, rate limiting, CORS, secrets handling for services like the ACIT gateway."
---

# FastAPI Security

## For this gateway (Track 02 defense)
- Identity via ES256 JWT signatures verified in Vault (no passwords).
- Mandate bounds + denylist checks before any action.
- IDPI sanitization in Firewall (before Guardrails).
- All external input treated as untrusted Protocol envelopes.
- Later: HTTP layer must refuse early with proper status + Audit.

## Recommended patterns
- Dependency injection for current_agent / current_mandate (after verification).
- Pydantic models for all request bodies (strict mode).
- No raw dicts for security-critical data.
- Use `cryptography` + `security-audit` for signing paths.
- CORS: restrict to known test clients.
- Rate limit at edge or middleware.

## Common pitfalls to avoid
- Trusting claims without signature verification.
- Logging sensitive fields.
- Broad exception handlers that leak stack traces.
- Constructing DB clients inside request handlers.

Use together with `security-audit`, `cryptography`, `python-expert`, `error-handling`, and `fastapi-templates`.
