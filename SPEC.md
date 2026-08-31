# ACIT Gateway Specification

## 1. Overview

The ACIT Gateway accepts a Protocol envelope from an Agent, verifies identity and Mandate bounds, sanitizes IDPI, enforces Merchant Guardrails, executes a Razorpay test-mode Money action or issues a Refusal, and writes an Audit event.

It is the inbound test-mode bridge for agentic commerce.

- Primary track: 01 (agentic commerce)
- Secondary track: 02 (defense-only IDPI)
- Tertiary track: 05 (infra)

All money uses integer paise. All times use timezone-aware UTC. Refusal with a reason_code is a successful, auditable outcome.

No LLM participates in any gate or Money action.

## 2. Requirements

### 2.1 Functional Requirements

- Parse AP2, TAP, P3P, and UAP Protocol envelopes into one canonical Mandate.
- Register Agents and store Mandates with cryptographic proof (ES256 JWT).
- Verify Mandate state: active, not expired, not revoked, not denylisted.
- Sanitize raw envelopes for IDPI and tool poisoning using deterministic rules before parsing.
- Enforce Guardrails on every Proposal against the Mandate and Catalog: amount, SKU allow-list, price match, discount bounds, no dark patterns.
- Execute only test-mode Razorpay Orders and Payments after all gates pass.
- Append an AuditEntry on every terminal path (allow or Refusal). The chain uses `hash = sha256(prev_hash || payload_json)`.
- Expose Catalog, health, envelope submission, and Audit query endpoints.
- Support revocation and denylist for Agents and Mandates.

### 2.2 Non-Functional Requirements

- Deterministic behavior only. No probabilistic or model-based decisions on the runtime path.
- Test-mode Razorpay keys exclusively. Zero live money.
- Reproducible runs via Docker.
- Verifiable audit chain on demand.
- Small public service interfaces. Tests exercise seams, not private SQL or helpers.
- Injected `db_path` (and later Razorpay client). No construction of infrastructure inside core services.

## 3. Architecture

### Request Flow

1. Agent sends Protocol envelope + ES256 JWT (kid == sub == agent_id).
2. C4 Prompt Firewall receives raw content, strips bidi/zero-width, rejects poison keys and substrings, recurses structures.
3. Clean envelope goes to C1 Protocol Abstraction.
4. C1 parses to InternalMandate (alias Mandate).
5. C3 Mandate Vault verifies signature and state (TTL, revocation, denylist).
6. C2 Semantic Catalog supplies price and max discount truth.
7. C5 Policy Engine evaluates Proposal against Mandate + Catalog + Guardrails.
8. On allow: execute test-mode Money action via Razorpay adapter.
9. C6 Audit Logger appends on every path with hash chain.
10. Response: `{ "allowed": bool, "reason_code": str | null, ... }`

C7 Chaos injects faults only at the Razorpay adapter. C8 exercises dark-pattern cases in tests.

See `docs/ARCHITECTURE.md` for Mermaid diagrams of flow, components, boundaries, and data models.

### Components (C1–C8)

- **C1 Protocol Abstraction**: `parse_envelope(protocol, envelope) -> Mandate`. Structure only. Emits `ProtocolParseError.reason_code`.
- **C2 Semantic Catalog**: Agent-readable offers. SKU → price, max_discount. Static or simple store for MVP.
- **C3 Mandate Vault**: `Vault(db_path)`. `register_agent`, `store_mandate`, `verify_signature`, `validate_mandate`, `revoke_mandate`, `is_denied`, `add_to_denylist`. ES256 JWT. Failures via `VaultError.reason_code`.
- **C4 Prompt Firewall**: Deterministic IDPI sanitizer on raw input. No LLM.
- **C5 Policy Engine / Guardrails**: Deterministic bounds, SKU, price, discount, and dark-pattern checks. Returns `PolicyResult`.
- **C6 Audit Logger**: Append-only SQLite. SHA-256 hash chain. Every allow and every Refusal writes here.
- **C7 Chaos**: Failure injection (timeout, 5xx, corrupt) against Razorpay adapter only. Graceful Refusal + Audit.
- **C8 Dark-Pattern Tests**: Explicit tests for false urgency, invented discounts, confirm-shaming, "no means no".

## 4. Data Models

Amounts are non-negative integers in paise. Timestamps are timezone-aware UTC.

### Foundational: Mandate (InternalMandate)

```python
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class Protocol(str, Enum):
    AP2 = "ap2"
    TAP = "tap"
    P3P = "p3p"
    UAP = "uap"

class OrderItem(BaseModel):
    sku: str
    quantity: int = Field(gt=0)
    unit_amount_paise: int = Field(ge=0)
    name: str | None = None

class Mandate(BaseModel):
    mandate_id: str
    agent_id: str
    user_id: str | None = None
    protocol: Protocol
    max_amount_paise: int = Field(ge=0)
    currency: str = "INR"
    sku_allowlist: list[str] = Field(min_length=1)
    expires_at: datetime
    items: list[OrderItem] = Field(default_factory=list)

InternalMandate = Mandate
```

Mandate is the single canonical spend authority object. Parser, Vault, Policy, Money action, and Audit operate on it.

### Other Core Models

- `Proposal`: mandate_id, items, quoted_total_paise, quoted_discount_paise, copy (strings scanned by Guardrails).
- `CatalogItem`: sku, name, unit_amount_paise, currency, max_discount_paise.
- `AgentIdentity`: agent_id, public_key_pem, created_at.
- `ValidationResult`: gate, allowed, reason_code.
- `PolicyResult`: mandate_id, allowed, reason_code, violations.
- `AuditEntry`: event_id, gate, reason_code, payload_json, prev_hash, hash, created_at.

All models are Pydantic v2. No untyped dicts stand in for Mandate.

## 5. API

Credentials:

- `X-API-Key`: Merchant / operator (from `.env`).
- `Authorization: Bearer <jwt>`: Agent identity on spend paths.

Error convention:

- 401/400 for auth or schema problems.
- 200 with `allowed: false` + `reason_code` for domain Refusals.
- Every terminal response is auditable.

Endpoints (reference):

| Method | Path              | Auth              | Purpose                              | Success response |
|--------|-------------------|-------------------|--------------------------------------|------------------|
| GET    | /health           | none              | Liveness                             | `{ "status": "ok" }` |
| GET    | /v1/catalog       | API key           | Agent-readable offers                | `{ "items": CatalogItem[] }` |
| POST   | /v1/agents        | API key           | Register Agent public key            | `{ "agent_id": "..." }` |
| POST   | /v1/envelopes     | API key + JWT     | Submit Protocol envelope + Proposal  | `{ "allowed": bool, "reason_code": str|null, "mandate_id": str|null, "payment": {...}|null, "validation": [...] }` |
| GET    | /v1/audit         | API key           | Query Audit chain (optionally by mandate_id) | `{ "entries": AuditEntry[], "chain_ok": bool }` |

See `docs/design.md` for request/response shapes and `EnvelopeRequest` / `EnvelopeResponse`.

## 6. Security

- All external input starts untrusted. C4 Firewall is the sanitization boundary.
- Agent identity: ES256 JWT. `kid` header equals `sub` claim equals registered `agent_id`. Public key from Vault only.
- Mandate bounds and state enforced in Vault (C3) and Policy (C5).
- Guardrails block false urgency, invented discounts, confirm-shaming, and post-refusal escalation.
- Audit is append-only. No UPDATE or DELETE on the chain.
- No LLM on Firewall, Vault, Guardrails, verification, Money action, or hashing.
- OWASP agentic risks addressed: Agent Identity (ASI01), Indirect Prompt Injection (ASI02), Over-privileged Mandates (ASI03), Catalog integrity (ASI05), Logging (ASI06).

## 7. Implementation

- Language and stack: Python 3.11+, FastAPI, Pydantic v2, SQLite (direct or SQLAlchemy Core), PyJWT + cryptography (ES256), Razorpay SDK (test keys only).
- Dependency injection: `db_path` supplied to Vault and Audit. Razorpay client injected at the execution seam.
- Phases (strict order, each ends with green tests):
  1. C1 Mandate + parser (AP2/TAP/P3P/UAP).
  2. C3 Vault + ES256 + SQLite agents/mandates/denylist.
  3. C2 Catalog + C4 Firewall.
  4. C5 Policy/Guardrails + C6 Audit.
  5. C6 Razorpay test-mode adapter.
  6. C7 Chaos + C8 Dark-pattern tests.
  7. Docs, video, submission.
- Build: `pytest tests/unit -q` (and later integration/chaos) must pass after each phase.
- Deep modules: small public seams. Tests hit interfaces.
- Conventional commits. No remote push unless requested.

See `PHASES.md`, `AGENTS.md`, `RULES.md`.

## 8. Acceptance Criteria

- `docker compose up` serves the Gateway.
- `pytest tests/unit tests/integration tests/chaos -q` is green.
- Poisoned Protocol envelope → Refusal with `idpi_detected` + Audit event.
- Over-limit, expired, SKU-not-allowed, or revoked Mandate → Refusal + Audit event.
- Valid bounded Proposal inside Mandate + Catalog → Razorpay test-mode order/payment ids present in response and Audit.
- Audit chain verifies: each hash equals `sha256(prev_hash || payload_json)`. Genesis uses 64 zeros.
- No live Razorpay keys or real money paths exist.
- No LLM calls on any gate or execution path.

## 9. Success Metrics

- Bounded, gated, explainable Money actions for Track 01.
- Honest defense-only IDPI Refusals for Track 02.
- Verifiable hash-chained Audit that survives chaos.
- Reproducible demo: one command to run, one command to test.
- "What broke at 2 AM" incident note derived from an actual run in the repo.
- Internal freeze 2026-09-04; Google Form submit 2026-09-05.

## References

- `CONTEXT.md` — ubiquitous language (read first)
- `docs/PRD.md`
- `docs/ARCHITECTURE.md`
- `docs/design.md`
- `AGENTS.md`, `RULES.md`, `PHASES.md`
- `docs/adr/`
