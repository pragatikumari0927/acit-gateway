---
name: production-readiness
description: Hardening checklist, observability, security defaults, graceful degradation, and release practices for Python/FastAPI services. Applies to test-mode Razorpay gateway before any real keys.
---

# Production Readiness

## For ACIT Gateway (defense-only, test-mode)
- All money actions gated behind Parser + Vault + Firewall + Guardrails.
- No LLM on any runtime path (ADR-0002).
- Secrets only via env / injected clients; never in code or logs.
- SQLite for now: use WAL mode, proper connection handling, migrations plan for later.
- Rate limiting, input size limits, and denylist enforcement early.
- Structured audit that is hash-chained (phase 7).

## Checklist (use before phase 9 show)
- [ ] All failure modes produce Refusal + Audit
- [ ] Chaos tests cover Razorpay test-mode failure injection
- [ ] Coverage >= 80% on core paths (parser, vault, firewall, guardrails)
- [ ] No direct sqlite construction outside injected db_path
- [ ] Dependency pins + pip-audit / safety in CI
- [ ] Docker multi-stage, non-root where possible (see docker-patterns)
- [ ] Logs safe, no PII/keys
- [ ] Graceful shutdown and DB cleanup

## CI / Deploy
Use `github-actions` + `git-github-flow`.

Combine with `security-audit`, `chaos-engineer`, `performance-optimizer`, `repo-health-check`.
