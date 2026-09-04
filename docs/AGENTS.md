# ACIT Gateway — agent instructions

> **Stale:** this file predates `run_execute`. Runtime `src/` and `tests/` are not empty stubs. Live pipeline: Firewall → parsed Mandate → Guardrails → Vault → Money action → Audit in `src/services/checkout.py` (`run_execute`); status in `docs/MEMORY.md`. Diagnosis: [TROUBLESHOOTING.md](TROUBLESHOOTING.md). Covenant: [SOUL.md](SOUL.md).

Inbound test-mode bridge: an Agent presents a Protocol envelope; the Gateway verifies identity and Mandate bounds, sanitizes IDPI, enforces Merchant Guardrails, then executes a Razorpay test-mode Money action or a Refusal, and writes an Audit event. Tracks: 01 (agentic commerce) primary, 02 (defense-only IDPI) secondary, 05 (infra) tertiary.

## Read first

- Language: `CONTEXT.md` (do not invent synonyms; `InternalMandate` is an alias of `Mandate`)
- Diagnosis: `TROUBLESHOOTING.md`
- Covenant: `SOUL.md`
- Scope: `PRD.md`
- Seams: `ARCHITECTURE.md`
- Decisions: `adr/`
- Short checklist: `RULES.md`
- Prompt-8 numbering: `PHASES.md`
- Progress: `MEMORY.md`

## Now

Design docs are in place (`ARCHITECTURE.md`, `design.md`, `CONTEXT.md`). **Runtime `src/` and `tests/` are empty skeleton stubs** — do not implement until a coding phase is requested. When coding starts, begin at C1 (Mandate + parser), then C3 (Vault).

## Constraints

- Internal freeze **4 September 2026**; Google Form submit **5 September 2026**.
- ₹0. Razorpay **test-mode keys only**.
- Python 3.11, FastAPI, SQLite, Pydantic v2, PyJWT, cryptography, Pytest, Docker, GitHub Actions.
- Track 02: defense-only. Offense-capable tooling is disqualified.

## Where not to use an LLM

No model on the runtime path (ADR-0002). Agents are **clients**. Do not put an LLM in Firewall, Guardrails, Mandate verification, Vault, Money actions, or audit hashing. “AI judgment” is this refusal.

## Intended seams (not implemented — `src/` is skeleton)

Contracts live in `design.md`. Do not assume these modules have bodies.

- **Parser** — `parse_envelope(protocol, envelope) -> Mandate` and `parse_ap2` / `parse_p3p` / `parse_tap` / `parse_uap`. Structure only. Failures: `ProtocolParseError.reason_code`. TAP is a project envelope; do not expand the acronym.
- **Vault** — `Vault(db_path)`: `register_agent`, `store_mandate`, `verify_signature`, `validate_mandate`, `revoke_mandate`, `is_denied`, `add_to_denylist`. Identity, TTL, revocation, denylist — not Guardrails. Failures: `VaultError.reason_code`.
- **Crypto** — `src/utils/crypto.py` ES256 (`generate_es256_keypair`, `sign_jwt`, `verify_jwt`).
- HTTP Refusal comes later. Until then, coded parse/vault errors are the outcome.

## Coding rules

- CONTEXT vocabulary in types, tests, and issue titles.
- Pydantic v2 models; no untyped dicts as Mandates.
- Deep services: small public interface; tests hit that interface, not SQL rows or private helpers.
- Inject `db_path` (and later Razorpay clients). Do not construct SQLite or Razorpay inside parser/policy/firewall.
- Parser checks structure. Vault checks identity/TTL/denylist. Policy/Guardrails come later.
- Money actions are gated: no Razorpay call unless Firewall, parser, Vault, and Guardrails all pass.
- Every later HTTP allow/Refuse writes an Audit event.

## Build phases

Do not skip. Each phase leaves tests green.

- [ ] 0 Bootstrap — `pyproject.toml`, deps, `.gitignore`
- [ ] 1 Mandate + parser — AP2 / TAP / P3P / UAP → `Mandate`
- [ ] 2 Vault — ES256 JWT, SQLite agents/mandates/denylist
- [ ] 3 Firewall — deterministic IDPI / tool-poison sanitizer
- [ ] 4 Guardrails / policy
- [ ] 5 Catalog
- [ ] 6 Razorpay test-mode adapter (chaos injects here only)
- [ ] 7 Hash-chained audit
- [ ] 8 Chaos + one graceful failure
- [ ] 9 Show — README, video, “what broke at 2 AM”

## Tests

```bash
pytest tests/unit -q
```

No unit tests until a coding phase lands. When they exist: unit tests hit service interfaces; integration hits FastAPI + temp SQLite; chaos faults the Razorpay adapter only.

## Git

Conventional commits (`feat(parser):`, `feat(vault):`, …). Do not push unless asked (no remote yet).

## Agent skills

Skills are now located in `.qwen/skills/` (consolidated from `.grok/skills/`, `.agents/skills/`, and `.claude/skills/`). Use `.qwenignore` to control file access for Qwen agents.

### Issue tracker

GitHub Issues via the `gh` CLI. External PRs are not a triage surface. See `agents/issue-tracker.md`.

### Triage labels

Canonical role names used as-is (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `adr/` at the repo root. See `agents/domain.md`.
