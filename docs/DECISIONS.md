# Architecture Decision Records — ACIT Gateway

This document records structural decisions. Each ADR follows the template:

- Status
- Date
- Context
- Decision
- Consequences
- Alternatives

All decisions respect the constraints in `CONTEXT.md`, `PRD.md`, `AGENTS.md`, and `RULES.md`. No LLM participates in money-critical paths. Test-mode only.

---

## ADR-001: Canonical Mandate as the only internal spend object

**Status:** accepted

**Date:** 2026-08-26

**Context:**  
Inbound Protocol envelopes (AP2, P3P, TAP, UAP) differ on the wire. Multiple parallel payment engines would duplicate every gate (Firewall, Vault, Policy, Audit) and make the Track 01 requirement of "bounded, gated, explainable" impossible to verify uniformly.

**Decision:**  
Parse every Protocol envelope into one `Mandate` (also called `InternalMandate`). All downstream components (Vault, Policy Engine, Money action, Audit) operate exclusively against this object. Adapters exist only in the parser.

**Consequences:**  
- Single source of truth for bounds (max_amount_paise, sku_allowlist, expires_at, agent_id).
- Tests and Audit become protocol-agnostic.
- Easy addition of new protocols without touching money or audit paths.
- Parser failures surface as `ProtocolParseError.reason_code`.

**Alternatives:**  
Per-protocol engines (rejected: duplication, unverifiable guarantees). Untyped dicts passed as "mandate" (rejected: violates Pydantic v2 rule and CONTEXT vocabulary).

---

## ADR-002: No LLM on the Money path

**Status:** accepted

**Date:** 2026-08-26

**Context:**  
Track 01 demands every Money action be bounded, gated, and explainable. Track 02 is defense-only IDPI prevention. An LLM inside Firewall, Vault, Guardrails, Mandate verification, Razorpay adapter, or audit hashing would be non-deterministic, unexplainable, and would disqualify the defense track.

**Decision:**  
Firewall, Vault, Guardrails, Mandate verification, Razorpay calls, and hashing use deterministic code only. Agents are clients that present envelopes. The evaluation criterion "AI judgment" is this explicit refusal to place models on the critical path.

**Consequences:**  
- All Refusals have a stable `reason_code` and are reproducible.
- Cost and latency are predictable (₹0 constraint).
- IDPI defense uses substring, structural, and character rules (C4).
- Easy to audit and test.

**Alternatives:**  
"LLM Firewall to catch novel jailbreaks" (rejected: non-deterministic, extra cost, wrong tool for gated money). Hybrid classifier (rejected for same reasons on MVP timeline).

---

## ADR-003: Append-only SHA-256 hash chain for Audit events

**Status:** accepted

**Date:** 2026-08-26

**Context:**  
Every terminal decision (allow or Refusal) must be explainable after the fact. Tamper evidence is required for the demo and for Track 01/02 claims. External log stores or Postgres outbox add complexity and cost.

**Decision:**  
Store Audit events as append-only rows in SQLite. Each row records `hash = sha256(prev_hash || payload_json)`. Genesis row uses 64 zero characters. Never UPDATE or DELETE Audit rows. C7 chaos is forbidden from touching the chain.

**Consequences:**  
- `GET /v1/audit` can return `chain_ok` by re-computing hashes.
- One simple verification function suffices for demo and tests.
- SQLite file under `data/` is acceptable for MVP.

**Alternatives:**  
Postgres + outbox or external ledger (rejected: violates ₹0, single-process, 10-day constraints). In-memory audit (rejected: no persistence across restarts).

---

## ADR-004: SQLite for Vault, Mandates, Denylist, and Audit (MVP)

**Status:** accepted

**Date:** 2026-08-27

**Context:**  
The project must run with `docker compose up`, zero external services, and zero cost. Full durability across restarts is required for Audit and Vault state.

**Decision:**  
Use a single SQLite file (or a small set of files) under `data/`. Tables for agents, mandates, denylist, and audit. Inject `db_path` into `Vault(db_path)` and Audit. Direct sqlite3 or minimal SQLAlchemy Core. No migrations framework for MVP.

**Consequences:**  
- Simple container image. No DB server.
- Tests use temp files or `:memory:`.
- Later swap to Postgres does not change Mandate shape or hash rule.
- Audit appends remain the integrity mechanism.

**Alternatives:**  
Embedded Postgres or external service (rejected: complexity and cost). Pure in-memory (rejected: no restart durability).

---

## ADR-005: FastAPI + Pydantic v2 as the service surface

**Status:** accepted

**Date:** 2026-08-26

**Context:**  
Need typed request/response models, dependency injection for `db_path` and clients, async-friendly paths, and excellent test support with httpx.

**Decision:**  
FastAPI for the HTTP edge. Pydantic v2 `BaseModel` for every seam model (Mandate, Proposal, AuditEntry, etc.). Use dependency injection and lifespan for resources. No raw dicts as Mandates.

**Consequences:**  
- Automatic validation and OpenAPI.
- Models are the source of truth shared by parser, policy, and tests.
- Clear separation between wire shapes and internal Mandate.

**Alternatives:**  
Flask + marshmallow or manual dict handling (rejected: weaker typing and validation). Django (rejected: overkill for this service shape).

---

## ADR-006: Phase-gated implementation with green tests after each phase

**Status:** accepted

**Date:** 2026-08-26

**Context:**  
Design docs exist. Runtime starts as skeleton. Risk of partial implementation, skipped gates, or broken Audit is high on a short timeline.

**Decision:**  
Follow `PHASES.md` strictly. Each phase delivers working public seams + unit tests. Run `pytest tests/unit -q` (later + integration/chaos) and leave the suite green before moving on. Begin with C1 (Mandate + parser) then C3 (Vault).

**Consequences:**  
- Parser and Vault exist before any Money action or Razorpay call.
- Refusals are real and tested early.
- No "big bang" integration at the end.

**Alternatives:**  
Feature branches that integrate everything at once (rejected: violates "each phase leaves tests green").

---

## ADR-007: Zero dark patterns in Guardrails

**Status:** accepted

**Date:** 2026-08-26

**Context:**  
Merchant Guardrails must block false urgency, invented discounts, confirm-shaming, and escalation after "no". These patterns appear in Proposal.copy and quoted values.

**Decision:**  
C5 Policy Engine performs deterministic substring and value checks against Catalog truth. Empty copy is allowed. No urgency strings are stored in Catalog unless they represent real constraints (MVP: they do not). C8 provides explicit failing tests for each pattern.

**Consequences:**  
- "No means no" is structural.
- Guardrails are explainable via `violations` list and `reason_code`.
- Dark-pattern tests are part of the required suite.

**Alternatives:**  
Rely on Merchant site copy or LLM review (rejected: not deterministic and not in scope).

---

## ADR-008: Injected dependencies only (db_path, clients)

**Status:** accepted

**Date:** 2026-08-27

**Context:**  
Services must remain testable and portable. Construction of SQLite connections or Razorpay clients inside parser, policy, firewall, or vault creates hidden coupling and breaks unit tests.

**Decision:**  
Every service receives `db_path` (and later a Razorpay client) via constructor or FastAPI dependency. No module-level globals or `sqlite3.connect()` calls inside core logic.

**Consequences:**  
- Unit tests pass temp paths or mocks.
- Integration tests control the database file.
- Clear ownership at the composition root.

**Alternatives:**  
Module-level singletons or factory functions inside services (rejected: hard to test and violates "inject db_path" rule).

---

## ADR-009: Python 3.11+ with strict typing and Google docstrings

**Status:** accepted

**Date:** 2026-08-26

**Context:**  
Project declares Python 3.11. Type hints, linting, and readable public interfaces improve maintainability on a small team and during handoff.

**Decision:**  
`requires-python = ">=3.11"`. Type hints on every public function. Pydantic v2 models carry the contracts. Google-style docstrings on public methods. Ruff + mypy in dev requirements and CI.

**Consequences:**  
- Early detection of shape errors.
- Models serve as living documentation.
- Consistent with AGENTS.md and RULES.md.

**Alternatives:**  
Dynamic Python without annotations (rejected: contradicts stated stack and testability goals).

---

## ADR-010: Docker and docker-compose for reproducible environments

**Status:** accepted

**Date:** 2026-08-26

**Context:**  
Submitters and reviewers must obtain identical behavior with one command. Local Python versions and OS differences must not affect results.

**Decision:**  
Provide `Dockerfile` (python:3.11-slim base) and `docker-compose.yml`. `.env` supplies only test-mode keys. `docker compose up --build` is the documented happy path.

**Consequences:**  
- "Works on my machine" disappears for the demo.
- CI can use the same image.
- Secrets stay out of the image via build args or runtime env only.

**Alternatives:**  
"pip install and run" only (rejected: fragile across reviewer machines).

---

## ADR-011: Refusal is a coded success, not an exception

**Status:** accepted

**Date:** 2026-08-27

**Context:**  
Domain-level rejection (expired Mandate, IDPI, invented discount) must still produce a full Audit event and a clean 200 response with `allowed: false`.

**Decision:**  
Return `ValidationResult` / `PolicyResult` / response objects carrying `allowed` and `reason_code`. Do not raise for expected Refusals. Only transport or infrastructure problems raise. Every Refusal path writes to C6.

**Consequences:**  
- Audit is complete for both happy and refusal paths.
- Client code (Agents) receives a stable shape.
- Tests assert on reason codes, not exception types.

**Alternatives:**  
HTTP 4xx/5xx for every refusal (rejected: blurs domain outcome with transport error; hides the "completed Refusal" semantics).

---

## ADR-012: PreToolUse hooks and .grokignore for session hygiene

**Status:** accepted

**Date:** 2026-08-28

**Context:**  
Agent sessions, traces, and secrets must never leak into context or git. Dangerous shell commands must be blocked before execution.

**Decision:**  
`.grokignore` excludes `.env*`, `*.pem`, `data/*.db`, `.grok/{hooks,sessions,traces}`, logs, build artifacts. Hooks (`validate-command.sh`, `security.json`) guard destructive or network-egress operations.

**Consequences:**  
- Memory mining and context stay clean.
- Accidental secret commits are prevented.
- Consistent with existing hook files in the tree.

**Alternatives:**  
Rely on developer discipline only (rejected: insufficient for automated agents).

---

## ADR-013: Test-mode Razorpay adapter with isolated chaos

**Status:** accepted

**Date:** 2026-08-29

**Context:**  
Money execution must be demonstrable, yet no real currency may move. Failures must be injectable for the "what broke at 2 AM" story.

**Decision:**  
Implement a thin adapter around the Razorpay test-mode SDK. Inject the client. C7 Chaos wraps only this adapter (timeout, 5xx, bad JSON). All other components remain untouched by chaos. Retries limited, idempotency via mandate_id.

**Consequences:**  
- Happy path shows real order_id / payment_id in Audit.
- Graceful degradation paths still write Audit entries.
- Production keys are never present in the repo.

**Alternatives:**  
Mock the entire payment layer in normal runs (rejected: demo would not exercise the actual SDK seam).

---

## Summary of Key Trade-offs

- Scope over features: defense-only, test-mode, deterministic.
- Simplicity over generality: SQLite + file audit, single process, injected seams.
- Verifiability over magic: hash chain, reason codes, no LLM judgment.
- Mandate as the foundational data structure that everything else protects.

These decisions protect future option value: swapping the database, adding protocols, or hardening the Firewall later does not require rewriting the core spend authority model or the audit rule.

See individual `adr/00*.md` for the short historical forms of the first three records.
