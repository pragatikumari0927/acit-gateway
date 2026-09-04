# Project Memory — ACIT Gateway

## 26 August 2026

### Project Started
- Context established
- Guidance files generated (`AGENTS.md`, `ARCHITECTURE.md`, `design.md`, `RULES.md`, `PHASES.md`, `MEMORY.md`) — all now in `docs/`

### Next Steps
- Begin Phase 1 (C1 and C3)

## 4 September 2026

### Phase 2.5 complete (policy, executor, v1 routes)
- Docs: CatalogItem in `design.md` / `SPEC.md` matches shipped percent `discount_bounds`; ARCHITECTURE C4 labels say refuse (soft hyphen normalised).
- Models: `AgentIdentity`, `AuditEntry` (mirrors `AuditRow`), `Proposal` (+ `merchant_id` for Catalog lookup), `PolicyResult.allowed`.
- `AgentIdentity.issuer` and `status` are API-only — not on `AgentRow`.
- C5 PolicyEngine first-failure-wins; C7 ChaosInjector with injected RNG; PaymentExecutor TEST MODE only, capture off by default.
- `/v1/catalog`, `/v1/mandates/*`, `/v1/checkout/*`, `/v1/audit/*`. Health and Razorpay webhook stay unprefixed.
- `pytest tests/ -q` → 85 passed. Coverage 88% (`--cov=src`; not a gate).
- Docker Compose skipped: Docker CLI 29.3.1 is installed, but the daemon is not running (`dockerDesktopLinuxEngine` pipe missing), so `/health` and `/` were not curled from a container.
- `scripts/vocab_check.py` flags substring `order` in `audit.py` (`order_by`), `chaos.py` (`razorpay_create_order`), and `firewall.py` (`reorder`). PaymentExecutor is not flagged because `rzp_test_` matches the checker's `test_` exclusion. Checker not edited.

### Flags
- No LLM on the money path. Razorpay test keys only.
- `AgentIdentity.issuer` / `status` are API-only (not persisted). `Proposal.merchant_id` is required for Catalog lookup and is not a DB column.
- Retry/chaos graceful-degradation path still open (PHASES Day 7 retry unchecked).
