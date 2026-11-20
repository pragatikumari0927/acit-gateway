# RULES

**ACIT Gateway — Coding and Project Rules for All Agents**

This is the short checklist referenced by AGENTS.md. **All agents (including Grok)** must follow these rules.

Authoritative language: [CONTEXT.md](CONTEXT.md). Full agent instructions and phases: [AGENTS.md](AGENTS.md). Scope and guardrails: [PRD.md](PRD.md). Architecture: [ARCHITECTURE.md](ARCHITECTURE.md).

## Coding Standards

- Python 3.11+, type hints on every function.
- Use Pydantic v2 for data validation.
- Docstrings on all public methods (Google style).
- PEP 8 compliance.
- No hard‑coded secrets; use environment variables.
- Strictly follow vocabulary from CONTEXT.md (Mandate, Protocol envelope, Agent, User, Merchant, Customer, Vault, Firewall, IDPI, Guardrail, Catalog, Money action, Audit event, Refusal). Do not invent synonyms. `InternalMandate` is an alias of `Mandate`.
- Pydantic v2 models at all seams; no untyped dicts as Mandates.
- Deep services with small public interfaces. Inject `db_path` (and later Razorpay clients). Never construct SQLite or Razorpay inside parser, policy, firewall, etc.
- Parser checks structure only. Vault checks identity, TTL, revocation, and denylist. Guardrails / policy come later.
- Money actions are gated: no Razorpay call unless Firewall, parser, Vault, and Guardrails all pass.
- Every terminal path (allow or Refusal) writes an Audit event.
- No LLM on the runtime path for Firewall, Vault, Guardrails, Mandate verification, Money actions, or audit hashing (ADR-0002). Agents are clients.
- Follow build phases in PHASES.md strictly. Do not skip ahead.

## Testing Rules

- Unit tests for every component (80%+ coverage).
- Integration tests for Razorpay API (use test‑mode only).
- Chaos tests with injected failures (only at the Razorpay adapter).
- Dark‑pattern tests (must pass before submission).
- Unit tests hit service public interfaces only, not SQL rows or private helpers.
- Refusal (with `reason_code`) is a coded success outcome, not a bare exception or error.
- `pytest tests/unit -q` (and later integration/chaos) must be green at the end of each phase.
- Poisoned Protocol envelope → Refusal + Audit. Over-limit/expired Mandate → Refusal + Audit. Audit chain must verify.

## Security Rules

- Never expose API keys in code.
- Validate all inbound payloads (Protocol envelopes → Mandate).
- Sanitize all user‑supplied text and IDPI/tool-poison (deterministic Firewall before parse).
- Use OWASP‑recommended practices for JWT (ES256) and cryptography.
- Hash-chained append-only Audit (SHA-256: `hash = sha256(prev_hash || payload)`) for integrity (ADR-0003).
- All security-critical paths are deterministic code (no models, no "AI judgment").

## Git & Documentation

- Commit frequently with clear, conventional messages (`feat(parser):`, `feat(vault):`, `docs(rules):`, …).
- Keep README updated.
- Maintain architecture diagrams (Mermaid in docs/ARCHITECTURE.md and design docs).
- Keep AGENTS.md, PHASES.md, MEMORY.md, and this RULES.md honest and in sync with reality.
- Do not push to remote unless explicitly asked.

## Dark Pattern Prohibition

These are non-negotiable Merchant Guardrails enforced before any Money action (see CONTEXT.md definition of Guardrail and PRD):

- No false urgency messages.
- No invented discounts.
- No confirm‑shaming.
- "No means no" — never escalate after a customer denies.

"Guardrail" is the correct term for merchant policy. Do not confuse with "Firewall" (IDPI sanitization only).

---

Additional details live in AGENTS.md (Coding rules + Build phases) and the ADRs. When in doubt, the source of truth is the combination of AGENTS.md + CONTEXT.md + this RULES.md.
