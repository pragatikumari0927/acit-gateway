# ACIT Gateway MVP — PRD

Razorpay AI Buildathon 2026. Primary: Track 01 (AI Growth & Agentic Commerce). Secondary: Track 02 (AI Risk Manager, defense-only). Tertiary: Track 05 (Open Track / infrastructure).

## Problem

Razorpay already has outbound AI payment execution (Vulcan, Agent Studio, MCP). It does not have an inbound agent-to-agent commerce bridge.

1. **Protocol fragmentation** — P3P is live, AP2 is deploying, NPCI UAP is in development. Razorpay has no inbound bridge across them.
2. **Identity and trust** — no cryptographic proof that an Agent acted inside a User Mandate. Liability is unclear.
3. **IDPI** — MCP tool poisoning (OWASP) can hide instructions in tool text and hijack an Agent into unauthorised Money actions.

## What we are building

A test-mode **ACIT Gateway**: any Agent presents a Protocol envelope; the Gateway verifies Agent identity and Mandate bounds, sanitizes IDPI, enforces Merchant Guardrails, executes via Razorpay test-mode APIs or issues a Refusal, and writes a hash-chained Audit event.

Happy path: discover Catalog → present Mandate → verify → sanitize → Guardrails → test-mode Money action → Audit event.

## In scope

- Canonical Mandate (max amount, SKU allow-list, TTL, Agent identity).
- Protocol envelopes: AP2-shaped and P3P-shaped for real; TAP and UAP mapped onto the same Mandate (not full spec clones).
- Vault verification of Agent identity material.
- Deterministic Firewall against IDPI / MCP tool poisoning.
- Merchant Guardrails: no invented discounts, no false urgency, bounds checks.
- Agent-readable Catalog.
- Razorpay test-mode Orders and Payments (UPI Reserve Pay if test keys allow).
- Append-only SHA-256 audit chain.
- One chaos/failure path that is Refused or recovered, and audited.

## Out of scope

- Live/production Razorpay keys or real money.
- Training or hosting an LLM in the Gateway.
- Offense-capable tooling (Track 02 disqualification).
- Byte-for-byte implementations of AP2, P3P, TAP, or UAP.
- Multi-tenant SaaS, billing, or a merchant dashboard beyond what the demo needs.

## Evaluation bars we must hit

| Criterion | How this MVP shows it |
|---|---|
| Problem taste | Inbound agent commerce is the open gap; Pine Labs already shipped P3P; NPCI is designing UAP. |
| Build quality | `docker compose up` runs; structured packages; pytest; hash-chained audit. |
| AI judgment | No LLM on Firewall, Vault, Guardrails, or Money actions. Agents are clients. |
| Failure recovery | Chaos at the Razorpay adapter; one graceful failure with an Audit event. |
| Track 01 | Every Money action bounded, gated, explainable. |
| Track 02 | Defense-only IDPI Refusal with honest tests (poisoned input → Refuse). |

## Acceptance

- `docker compose up` serves the Gateway.
- `pytest tests/unit tests/integration tests/chaos` is green.
- Poisoned Protocol envelope → Refusal + Audit event.
- Over-limit or expired Mandate → Refusal + Audit event.
- Happy-path Mandate → Razorpay test-mode order/payment id in the Audit event.
- Audit chain verifies (`hash = sha256(prev_hash \|\| payload)`).

## Deliverables (later phases)

- Public GitHub repo (this tree).
- 5-minute unlisted video of it working.
- Google Form, with “what broke at 2 AM” written from a real incident in this repo.

## Deadlines

- Internal freeze: 4 September 2026.
- Official submit: 5 September 2026.
