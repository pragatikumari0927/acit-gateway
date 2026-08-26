# ACIT Gateway — agent instructions

Inbound test-mode bridge: any Agent presents a Protocol envelope; the Gateway verifies identity and Mandate bounds, sanitizes IDPI, enforces Merchant Guardrails, then executes a Razorpay test-mode Money action or a Refusal, and writes an Audit event. Primary track 01 (agentic commerce). Secondary track 02 (defense-only IDPI). Tertiary track 05 (infra).

Read `CONTEXT.md` before naming a domain concept. Read `docs/adr/` before contradicting an architectural decision. Read `docs/ARCHITECTURE.md` before adding a package. Product scope is `docs/PRD.md`.

## Constraints

- Deadline: internal freeze **4 September 2026**; Google Form submit **5 September 2026**.
- Budget: ₹0. Razorpay **test-mode keys only**. No paid APIs, no cloud bills.
- Stack: Python 3.11, FastAPI, SQLite, Pydantic v2, PyJWT, cryptography, Pytest, Docker, GitHub Actions.
- Track 02 bar: defense-only. Anything offense-capable is disqualified.

## Where not to use an LLM

The runtime MVP has **no model on the path**. Agents are clients of this Gateway, not components inside it.

Do **not** put an LLM in: Firewall, Guardrails, Mandate verification, Vault, Money actions, or audit hashing. Those are deterministic. The evaluation criterion “AI judgment” is exactly this refusal.

## Coding rules

- Ubiquitous language from `CONTEXT.md` in types, routes, test names, and issue titles.
- Pydantic v2 models at the HTTP seam. Domain objects live in `src/models/`.
- Services are deep modules: small interface, behaviour hidden, tested through that interface (`src/services/`).
- Accept dependencies; do not construct Razorpay clients or SQLite connections inside business logic.
- Money actions are gated: no Razorpay call unless Vault, Firewall, Mandate bounds, and Guardrails all pass.
- A Refusal is a successful outcome with a coded reason — not an unhandled exception.
- Every decision (allow or Refuse) writes an Audit event.
- No invented discounts, no false urgency in Catalog or Agent-facing copy.

## Build phases

Do not skip ahead. Each phase leaves tests green.

0. **Bootstrap** — `pyproject.toml`, lockable deps, `.env.example`, SQLite path under `data/`, Docker Compose, GitHub Actions pytest.
1. **Mandate + parser** — canonical Mandate; Protocol envelopes for AP2-shaped and P3P-shaped payloads; TAP and UAP map to the same Mandate.
2. **Vault** — verify Agent JWT / key material; unsigned or unknown Agent → Refusal.
3. **Firewall** — deterministic IDPI / tool-poison sanitizer; poisoned envelopes Refuse and audit.
4. **Guardrails** — amount, SKU allow-list, TTL, no invented discounts, no false urgency.
5. **Catalog** — agent-readable offers the Merchant actually sells.
6. **Razorpay adapter** — test-mode Orders / Payments; UPI Reserve Pay if test keys allow. Chaos injects here only.
7. **Audit** — append-only SQLite rows, `hash = sha256(prev_hash || payload)`.
8. **Chaos + failure** — one graceful downstream failure with an Audit event and a clear Refusal or retry story.
9. **Show** — public README, architecture in `docs/ARCHITECTURE.md`, 5-minute video script, “what broke at 2 AM”.

## Tests

```bash
pytest tests/unit tests/integration tests/chaos -q
```

Unit tests hit service interfaces. Integration tests hit FastAPI with a test SQLite file. Chaos tests fault the Razorpay adapter, not production. A poisoned Protocol envelope must Refuse; an over-limit Mandate must Refuse; the audit chain must verify.

## Agent skills

### Issue tracker

GitHub Issues via the `gh` CLI. External PRs are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical role names used as-is (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
