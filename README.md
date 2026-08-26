# ACIT Gateway

Test-mode bridge: an AI Agent presents a Mandate; this Gateway verifies identity and bounds, sanitizes IDPI, enforces Merchant Guardrails, then executes a Razorpay **test-mode** payment or a Refusal. Everything is written to a SHA-256 hash-chained audit trail.

Razorpay AI Buildathon 2026 — Track 01 (agentic commerce) primary, Track 02 (defense-only IDPI) secondary, Track 05 (infra) tertiary.

> Test mode only. No live money.

## Why

P3P is live, AP2 is deploying, NPCI UAP is in development. Razorpay can execute agent payments outbound; it does not yet ingest those protocols inbound with cryptographic Mandate bounds and an IDPI Firewall.

## How it works

```
Protocol envelope → Firewall → Parser → Mandate → Vault → Guardrails → Razorpay test-mode → Audit
```

Language: [`CONTEXT.md`](CONTEXT.md). Product: [`docs/PRD.md`](docs/PRD.md). Seams: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Decisions: [`docs/adr/`](docs/adr/).

## Status

Guidance and architecture are in place. Runtime is built in the phases listed in [`AGENTS.md`](AGENTS.md). Until phase 0+ lands, `docker compose up` and `pytest` are the target interface, not a claim that empty stubs already serve traffic.

## Run (target)

```bash
cp .env.example .env   # Razorpay test keys only
docker compose up --build
```

API: `http://localhost:8000`

```bash
pytest tests/unit tests/integration tests/chaos -q
```

## Guardrails (non-negotiable)

- No LLM on Firewall, Vault, Guardrails, or Money actions.
- Every Money action is bounded, gated, and explainable — or it is a Refusal.
- Track 02 is defense-only. No offense-capable tools.
- Audit events are append-only.

## License

Student Buildathon project. Not an official Razorpay product.
