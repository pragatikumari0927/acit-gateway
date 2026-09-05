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

### Memory refresh (live repo)

Ground truth at commit `5e7719b` (`main`). Working tree dirty (execute pipeline + docs/skills uncommitted). `pytest -q` → **98 passed**.

- MemPalace re-indexed with project files and this log.
- Vocabulary Audit complete (CONTEXT vocabulary; `scripts/vocab_check.py` still flags `order` substrings).
- PyJWT kept (fastauth-py incompatible). ES256 via PyJWT + cryptography.
- SQLModel + aiosqlite in `src/db/` (evolution of ADR-004 SQLite; no new ADR file).
- Component status: C1 Parser ✅ C2 Catalog ✅ C3 Vault ✅ C4 Firewall ✅ C5 Policy ✅ C6 Audit ✅ C7 Chaos ✅ C8 dark-pattern tests ✅.
- C4 zero-width **fixed** (ADR-0004: refuse invisible chars; soft hyphen normalised). Do not persist the stale 36/37 / C4-failing brief.
- Execute pipeline: `run_execute` (Firewall → parsed Mandate → Guardrails → Vault → Money action → Audit). Checkout Refusals share `CheckoutExecuteResult` / `PolicyResult`. Vault/Audit process-cached; Razorpay client injected at DI.
- `SECURITY.md` at repo root. Docs canonical under `docs/` (CONTEXT, SPEC, DECISIONS, ARCHITECTURE, adr/).
- `providers.json`: mempalace + ai-memory + tavily enabled. `ai-memory` / `engram` CLIs not assumed present.

### Current status
- Tests: 104 passed (adds chaos graceful-path proof test: Refusal + audit + verify_chain). Supersedes 103.
- Open: Phase 5 (README/video/form), Day 7 retry still unchecked, webhook body still TODO.
- Next: submission polish, not start C5.

### Next steps
- Complete chaos retry + one graceful failure (Refusal + verified Audit chain).
- Phase 5 docs, demo video, Google Form submit.
- Freeze 4 Sep 2026; submit 5 Sep 2026.

### Backlog (out of current PR)
- ruff==0.1.0 is old; Phase 0 only cleared existing F401/F541/E402 so CI can gate. Bump later.
- Dirty local `uv.lock` (SQLModel restage) — do not mix into CI PR.
- Dependabot volume — Phase 2.
