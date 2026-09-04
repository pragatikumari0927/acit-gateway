# Soul

ACIT Gateway: an inbound test-mode bridge where an Agent presents a Protocol envelope, and deterministic code either performs a Razorpay Money action or issues a Refusal, then writes an Audit event.

## Core Identity

This repo is the Gateway, not a hosted model. Agents propose; `run_execute` in `src/services/checkout.py` disposes. A Refusal (`PolicyResult`: `allowed`, `reason_code`, `violations`, `mandate_id` in `src/models/proposal.py`) and an Audit event are product outcomes, not crash paths. The User authorised the Mandate; the Merchant’s Catalog and Guardrails bound the spend; live Razorpay keys are forbidden.

## Core Principles

1. **Refuse loudly, never silently.** `PolicyResult.allowed` is the only green light for a Money action (`src/models/proposal.py`). Firewall, parse, Guardrail, Vault miss, and executor failure all return a coded Refusal from `run_execute`.
2. **No LLM on the money path.** Firewall, Vault, Guardrails, Mandate checks, Razorpay, and Audit hashing are deterministic (`docs/adr/0002-no-llm-on-money-path.md`; `src/services/checkout.py` header). Agents are clients.
3. **Every request writes Audit, including Refusals.** `_audit_refusal` then `_refuse` on fail-closed branches; allow path calls `audit.log_entry` (`src/services/checkout.py`, `src/services/audit.py` SHA-256 chain).
4. **Test mode is the only mode.** `get_razorpay_client` raises `RuntimeError("Razorpay TEST MODE only")` unless `RAZORPAY_KEY_ID` starts with `rzp_test_` (`src/api/dependencies.py`).
5. **A Protocol envelope is untrusted until the Firewall passes it.** `idpi_detected` is a Refusal, not a strip-and-continue on invisible/bidi payloads (`src/services/firewall.py`).
6. **Deep module, thin HTTP.** Routes adapt status codes; `run_execute` owns Firewall → parsed Mandate → Guardrails → Vault → `asyncio.to_thread` Money action → Audit.
7. **Money handling must be idempotent — and today it is not, across process death.** Webhook dedupe is `_idempotency_keys` in `src/main.py` (in-memory). Single worker; reconcile after restart. An injectable store is a gap, not a feature.

## How Agents Work in This Repo

Verify a path or flag in the tree before claiming it. Money-path edits (`src/services/checkout.py`, Firewall, Vault, Guardrails, executor, webhook verify) need explicit user intent plus a test that goes red on the bug. Never invent APIs. Agent-facing docs (`docs/AGENTS.md`, this file, `docs/TROUBLESHOOTING.md`) are executable context — stale sentences are bugs. Secrets stay out of chat and logs; keys come from the environment.

## Document Relationships

`AGENTS.md` / `docs/AGENTS.md` = how (operating rules; `docs/AGENTS.md` is stale vs `run_execute` — see `docs/TROUBLESHOOTING.md`). `SECURITY.md` = threats and private disclosure. `SOUL.md` = why, when those files are silent. Conflict order: money-path safety > Audit integrity > developer convenience.

> Structure adapted from [affaan-m/ECC](https://github.com/affaan-m/ECC)'s SOUL.md (MIT).
