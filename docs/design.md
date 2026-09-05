# ACIT Gateway design

Detailed contracts for C1–C8. Request path and component map: [`ARCHITECTURE.md`](ARCHITECTURE.md). Glossary: [`CONTEXT.md`](CONTEXT.md).

**Implemented today:** C1 Mandate/parser, C3 Vault/ES256. Snippets marked *intended* are the interfaces later phases must implement — do not treat them as shipping code.

`InternalMandate` is an alias of **Mandate**. `AuditEntry` is the class name for an **Audit event**. A **Proposal** is the Agent’s proposed Money action (lines, quoted price, copy) evaluated *against* a Mandate — not a second Mandate.

---

## 1. Data models

Amounts are **integer paise**. Timestamps are timezone-aware UTC.

### `OrderItem` and `InternalMandate` (shipping)

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

### `Proposal` *(intended)*

What the Agent wants to buy **now**, inside an existing Mandate.

```python
class Proposal(BaseModel):
    mandate_id: str
    merchant_id: str  # Catalog lookup key; not a DB column
    items: list[OrderItem]
    quoted_total_paise: int = Field(ge=0)
    quoted_discount_paise: int = Field(ge=0, default=0)
    copy: list[str] = Field(default_factory=list)  # Agent-facing strings C5 scans
```

### `CatalogItem` *(intended)*

An offer the Merchant actually sells. Source of truth for price and allowed discount.

```python
class DiscountBounds(BaseModel):
    min_percent: int = Field(ge=0, le=100)
    max_percent: int = Field(ge=0, le=100)

class CatalogItem(BaseModel):
    sku: str
    name: str
    description: str = ""
    unit_amount_paise: int = Field(ge=0)
    inventory: int = Field(ge=0)
    discount_bounds: DiscountBounds
    categories: list[str] = Field(default_factory=list)
```

### `AgentIdentity` *(intended; Vault `agents` row)*

```python
class AgentIdentity(BaseModel):
    agent_id: str
    public_key_pem: str
    created_at: datetime
```

### `ValidationResult` *(intended)*

One gate’s outcome. Refusal is `allowed=False` plus a reason code — not an HTTP 5xx.

```python
from typing import Literal

Gate = Literal["firewall", "parser", "vault", "policy", "razorpay"]

class ValidationResult(BaseModel):
    gate: Gate
    allowed: bool
    reason_code: str | None = None  # e.g. idpi_detected, expired, invented_discount
```

### `PolicyResult` *(intended)*

C4 output. `allowed=True` is the only green light for C6.

```python
class PolicyResult(BaseModel):
    mandate_id: str
    allowed: bool
    reason_code: str | None = None
    violations: list[str] = Field(default_factory=list)
```

### `AuditEntry` *(intended; Audit event)*

```python
class AuditEntry(BaseModel):
    event_id: str
    gate: Gate
    reason_code: str
    payload_json: str
    prev_hash: str  # 64 hex chars; genesis is 64 zeros
    hash: str       # sha256(prev_hash || payload_json)
    created_at: datetime
```

---

## 2. API design

FastAPI edge, not yet implemented. Two credentials:

| Header | What it proves |
| --- | --- |
| `X-API-Key` | Merchant/operator may call this Gateway (shared test secret from `.env`) |
| `X-API-Key` with `AUDIT_ADMIN_API_KEY` | Operator credential carrying the server-assigned `audit:admin` scope |
| `Authorization: Bearer <jwt>` | **Agent** ES256 JWT (`kid`/`sub` = `agent_id`) on spend paths |

Missing/wrong API key → **401**. Unknown `protocol` → **400**. Gate Refusal → **200** `{ "allowed": false, "reason_code": "..." }` (Refusal is a completed outcome).

| Method | Path | Auth | Body / query | Success |
| --- | --- | --- | --- | --- |
| `GET` | `/health` | none | — | `{ "status": "ok" }` |
| `GET` | `/v1/catalog` | API key | — | `{ "items": CatalogItem[] }` |
| `POST` | `/v1/agents` | API key | `{ "agent_id", "public_key_pem" }` | `{ "agent_id" }` |
| `POST` | `/v1/envelopes` | API key + JWT | `{ "protocol", "envelope", "proposal"? }` | see below |
| `GET` | `/v1/audit` | API key | `?mandate_id=` | `{ "entries": AuditEntry[], "chain_ok": bool }` |
| `GET` | `/v1/audit/export` | API key + `audit:admin` scope | — | `{ "entries": AuditEntry[], "chain_ok": true }` |

```python
class EnvelopeRequest(BaseModel):
    protocol: Protocol
    envelope: dict
    proposal: Proposal | None = None

class EnvelopeResponse(BaseModel):
    allowed: bool
    reason_code: str | None = None
    mandate_id: str | None = None
    validation: list[ValidationResult] = Field(default_factory=list)
    payment: dict | None = None  # {"order_id", "payment_id"} test-mode only
```

Pipeline for `POST /v1/envelopes`: C2 sanitize → C1 parse → C3 verify JWT + `validate_mandate` → C4 `evaluate(mandate, proposal, catalog)` → C6 Money action → C7 append. Any Refuse still appends C7 and returns `allowed: false`.

---

## 3. Policy engine

Deterministic C4. No LLM. Catalog is the price list; Mandate is the spend envelope; Proposal is this attempt.

| Rule | Fail `reason_code` |
| --- | --- |
| Mandate stored and `status=active` | `unknown_mandate` / `revoked` |
| Agent registered and not denylisted | `unknown_agent` / `denied` |
| `now < mandate.expires_at` | `expired` |
| Every Proposal SKU ∈ `mandate.sku_allowlist` | `sku_not_allowed` |
| Every Proposal SKU ∈ Catalog | `sku_not_in_catalog` |
| Line `unit_amount_paise` == `CatalogItem.unit_amount_paise` | `invented_price` |
| `quoted_total_paise` ≤ `mandate.max_amount_paise` | `over_limit` |
| `quoted_discount_paise` ≤ sum of line `unit_amount_paise * quantity * max_percent // 100` | `invented_discount` |
| `copy` has no dark-pattern hits (below) | `false_urgency` / `confirm_shaming` |

Vault already enforces active / TTL / denylist at C3; C4 repeats TTL/amount/SKU against **Proposal** totals so a live Mandate cannot be overspent in one shot.

```python
def evaluate(mandate: Mandate, proposal: Proposal, catalog: dict[str, CatalogItem]) -> PolicyResult:
    violations: list[str] = []
    if proposal.mandate_id != mandate.mandate_id:
        violations.append("mandate_mismatch")
    if proposal.quoted_total_paise > mandate.max_amount_paise:
        violations.append("over_limit")
    for item in proposal.items:
        if item.sku not in mandate.sku_allowlist:
            violations.append("sku_not_allowed")
        offer = catalog.get(item.sku)
        if offer is None:
            violations.append("sku_not_in_catalog")
        elif item.unit_amount_paise != offer.unit_amount_paise:
            violations.append("invented_price")
    # dark-pattern + discount checks omitted here — see §6
    allowed = not violations
    return PolicyResult(
        mandate_id=mandate.mandate_id,
        allowed=allowed,
        reason_code=None if allowed else violations[0],
        violations=violations,
    )
```

---

## 4. Security

### JWT (shipping C3)

ES256. `kid` in the header; `sub` must equal `kid`. Public key from Vault; never trust an embedded PEM in the envelope.

```python
token = sign_jwt(payload, private_pem, kid=agent_id)
claims = verify_jwt(token, public_pem)  # InvalidToken → VaultError("invalid_signature")
```

### Audit hash (intended C7)

```python
import hashlib

GENESIS = "0" * 64

def chain_hash(prev_hash: str, payload_json: str) -> str:
    return hashlib.sha256(f"{prev_hash}{payload_json}".encode()).hexdigest()
```

### IDPI sanitisation (intended C2)

Deterministic, on the **raw** envelope, before C1:

1. Reject keys named `instructions`, `system`, `tool_description`, `developer_message`.
2. Refuse bidi / zero-width code points (`\u200b–\u200f`, `\u202a–\u202e`, `\u2060`, `\ufeff`). An invisible character in an untrusted envelope is itself IDPI; stripping it silently would mutate the input and leave no Refusal ([ADR-0004](adr/0004-refuse-invisible-characters.md)). Exception: `\u00ad` (soft hyphen) is a legitimate line-break hint in Catalog product text — normalised away, not refused.
3. Substring denylist on all string values (case-insensitive), e.g. `ignore previous`, `you are now`, `exfiltrate`, `<hidden>`. Match on the stripped text so a phrase split by an invisible character (`ig\u00adnore previous`) still hits.
4. Recurse into lists/dicts; do not follow URLs or fetch tool manifests.

Hit → `ValidationResult(gate="firewall", allowed=False, reason_code="idpi_detected")` + Audit event. No LLM classifier ([ADR-0002](adr/0002-no-llm-on-money-path.md)).

---

## 5. Error handling and graceful degradation

| Layer | Behaviour |
| --- | --- |
| C2 / C1 / C3 / C4 | No retries. A Refuse is final for that request. Retrying would replay poison or a dead Mandate. |
| C6 Razorpay | At most **2 retries**, exponential backoff (100ms, 400ms), same idempotency key (`mandate_id`). Then Refuse `razorpay_unavailable`. |
| C8 Chaos | Faults **C6 only** (timeout / 5xx / empty body). Never C2/C3, never mutates C7. |
| C7 | `append` on every path including Refuse. If SQLite write fails, process logs the JSON line to stderr **and** re-raises — do not execute C6 without an Audit event. |
| HTTP | 401/400 for auth/schema; 200 + `allowed=false` for domain Refusal; 503 if C6 exhausted retries. |

```python
def execute_with_retry(adapter, mandate, *, attempts=3):
    last = None
    for i in range(attempts):
        try:
            return adapter.execute_money_action(mandate)
        except DownstreamError as exc:
            last = exc
            sleep(0.1 * 4**i)
    raise last
```

---

## 6. Dark-pattern prevention

C4 scans `Proposal.copy` and quoted money — not the LLM, not the Merchant’s marketing site. Catalog is the only legal price/discount.

| Pattern | Detection | `reason_code` |
| --- | --- | --- |
| False urgency | Copy matches `only \d+ left`, `expires in \d+ (sec\|min)`, `act now`, `last chance` (case-insensitive) when Catalog has no such constraint | `false_urgency` |
| Invented discount | `quoted_discount_paise > 0` and exceeds sum of line `unit_amount_paise * quantity * max_percent // 100`, or line price ≠ Catalog | `invented_discount` / `invented_price` |
| Confirm-shaming | Copy matches `no.? thanks, i (hate\|don't want) savings`, `i like paying more` | `confirm_shaming` |

Empty `copy` is allowed. C5 must not store urgency strings on `CatalogItem` unless they are real inventory constraints (MVP: they are not — Catalog is sku/price/discount only).

---

## 7. Audit trail

Append-only SQLite. `hash = sha256(prev_hash || payload_json)`. First row uses `prev_hash = 0*64`. Never `UPDATE`/`DELETE` ([ADR-0003](adr/0003-sqlite-hash-chain-audit.md)).

```python
def append(conn, gate: str, reason_code: str, payload_json: str) -> AuditEntry:
    prev = conn.execute("SELECT hash FROM audit ORDER BY rowid DESC LIMIT 1").fetchone()
    prev_hash = prev[0] if prev else GENESIS
    digest = chain_hash(prev_hash, payload_json)
    # INSERT only
    ...
```

`GET /v1/audit` recomputes the chain and returns `chain_ok`. C8 must not rewrite history. Every allow and every Refusal is an Audit event (Track 01 explainability, Track 02 IDPI evidence).
