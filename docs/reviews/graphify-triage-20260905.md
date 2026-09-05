# Graphify report triage — 2026-09-05

Triaged `graphify-out/GRAPH_REPORT.md` (last write 2026-09-05 09:19, corpus `src/` + `tests/`) against newest `src` commit `512f85d` (2026-09-05). Interactive twin: `graphify-out/graph.html`. Cross-checked against the Known-Broken registry in `docs/TROUBLESHOOTING.md`. Artifact hygiene: `graphify-out/`, `.graphify_*`, and `graphify-out/GRAPH_REPORT.html` appended to `.gitignore` (option a).

## Summary

Counts: **17 Confirmed** / **10 Refuted (false)** / **1 Unverifiable** / **0 Refuted (stale)**.

Trust: the 2026-09-05 `src+tests` graph names the real Gateway hubs (`PolicyEngine`, `Vault`, `Mandate`, `run_execute` callers) and is usable; 10 of 28 claims are extractor noise (docstring isolates, test-helper "surprises", INFERRED edges that leak route `Depends` onto `CheckoutExecuteRequest` or the unused `Vault` import onto MCP types). Do not treat god-node degree or inferred MCP/Vault edges as coupling bugs.

### F1 — Corpus may not need a graph (claim R1)
- Report claim: Corpus is ~5,568 words and may not need a graph.
- Verdict: Unverifiable
- Priority: None
- Classification: n/a
- Recommendation: ignore

### F2 — Thin communities omitted and unlabeled (claim R2)
- Report claim: 30 communities, 3 thin omitted; hubs 19–21 left as "Community N".
- Verdict: Confirmed
- Priority: P3 (hygiene)
- Proof: `src/db/__init__.py:1`
- Classification: n/a
- Recommendation: ignore

### F3 — 27 percent inferred edges (claim R3)
- Report claim: 181 of 679 edges are INFERRED (avg confidence 0.73).
- Verdict: Confirmed
- Priority: P3 (hygiene)
- Proof: `src/api/routes/checkout.py:29`
- Classification: leaked ordering
- Recommendation: ignore

### F4 — PolicyEngine god node (claim R4)
- Report claim: `PolicyEngine` is the most-connected node (23 edges).
- Verdict: Confirmed
- Priority: None
- Proof: `src/services/policy.py:46`
- Classification: n/a
- Recommendation: ignore

### F5 — CatalogService god node (claim R5)
- Report claim: `CatalogService` is a god node (21 edges).
- Verdict: Confirmed
- Priority: None
- Proof: `src/services/catalog.py:15`
- Classification: n/a
- Recommendation: ignore

### F6 — Vault god node (claim R6)
- Report claim: `Vault` is a god node (21 edges).
- Verdict: Confirmed
- Priority: None
- Proof: `src/services/vault.py:29`
- Classification: n/a
- Recommendation: ignore

### F7 — Mandate god node (claim R7)
- Report claim: `Mandate` is a god node (20 edges).
- Verdict: Confirmed
- Priority: None
- Proof: `src/models/mandate.py:29`
- Classification: n/a
- Recommendation: ignore

### F8 — AuditLogger god node (claim R8)
- Report claim: `AuditLogger` is a god node (17 edges).
- Verdict: Confirmed
- Priority: None
- Proof: `src/services/audit.py:48`
- Classification: n/a
- Recommendation: ignore

### F9 — OrderItem god node (claim R9)
- Report claim: `OrderItem` is a god node (16 edges).
- Verdict: Confirmed
- Priority: None
- Proof: `src/models/mandate.py:22`
- Classification: n/a
- Recommendation: ignore

### F10 — ChaosInjector god node (claim R10)
- Report claim: `ChaosInjector` is a god node (16 edges).
- Verdict: Confirmed
- Priority: None
- Proof: `src/services/chaos.py:13`
- Classification: n/a
- Recommendation: ignore

### F11 — PromptFirewall god node (claim R11)
- Report claim: `PromptFirewall` is a god node (15 edges).
- Verdict: Confirmed
- Priority: None
- Proof: `src/services/firewall.py:94`
- Classification: n/a
- Recommendation: ignore

### F12 — parse_envelope god node (claim R12)
- Report claim: `parse_envelope()` is a god node (15 edges).
- Verdict: Confirmed
- Priority: None
- Proof: `src/services/protocol_parser.py:24`
- Classification: n/a
- Recommendation: ignore

### F13 — PaymentExecutor god node (claim R13)
- Report claim: `PaymentExecutor` is a god node (13 edges) and a thin Razorpay wrapper.
- Verdict: Confirmed
- Priority: None
- Proof: `src/services/executor.py:17`
- Classification: shallow module
- Recommendation: ignore

### F14 — Surprising DiscountBounds test call (claim R14)
- Report claim: `test_discount_bounds_valid_construction()` calling `DiscountBounds` is surprising.
- Verdict: Refuted (false)
- Priority: None
- Classification: n/a
- Recommendation: ignore

### F15 — Surprising DiscountBounds reject test (claim R15)
- Report claim: `test_discount_bounds_validation_rejects_bad_range()` calling `DiscountBounds` is surprising.
- Verdict: Refuted (false)
- Priority: None
- Classification: n/a
- Recommendation: ignore

### F16 — Surprising _proposal in checkout tests (claim R16)
- Report claim: `_proposal()` in checkout unit tests calling `OrderItem` is surprising.
- Verdict: Refuted (false)
- Priority: None
- Classification: n/a
- Recommendation: ignore

### F17 — Surprising _proposal in executor tests (claim R17)
- Report claim: `_proposal()` in executor unit tests calling `OrderItem` is surprising.
- Verdict: Refuted (false)
- Priority: None
- Classification: n/a
- Recommendation: ignore

### F18 — Surprising mandate construction test (claim R18)
- Report claim: `test_mandate_valid_construction_and_alias()` calling `OrderItem` is surprising.
- Verdict: Refuted (false)
- Priority: None
- Classification: n/a
- Recommendation: ignore

### F19 — Low-cohesion proposal/policy community (claim R19)
- Report claim: Community 0 "Proposal Policy Models" has cohesion 0.1.
- Verdict: Confirmed
- Priority: None
- Proof: `src/models/mandate.py:29`
- Classification: n/a
- Recommendation: ignore

### F20 — Audit export stub (claim R20)
- Report claim: Full Audit export is a stub; chain verification lives on `AuditLogger.verify_chain`.
- Verdict: Confirmed
- Priority: P2 (architecture debt)
- Proof: `src/api/routes/audit.py:41`
- Classification: dead interface
- Recommendation: ticket-worthy fix

### F21 — Isolated nodes as undocumented components (claim R21)
- Report claim: 123 isolated nodes are missing edges or undocumented components.
- Verdict: Refuted (false)
- Priority: P3 (hygiene)
- Classification: n/a
- Recommendation: ignore

### F22 — Mandate as cross-community bridge (claim R22)
- Report claim: `Mandate` bridges tests, parser, vault, executor, and mandate routes (betweenness 0.200).
- Verdict: Confirmed
- Priority: None
- Proof: `src/models/mandate.py:29`
- Classification: n/a
- Recommendation: ignore

### F23 — CheckoutExecuteRequest as bridge (claim R23)
- Report claim: `CheckoutExecuteRequest` bridges policy, vault, audit, executor, firewall, and checkout execute.
- Verdict: Refuted (false)
- Priority: None
- Classification: leaked ordering
- Recommendation: ignore

### F24 — PaymentExecutor bridges Mandate Tests (claim R24)
- Report claim: `PaymentExecutor` unexpectedly bridges Payment Executor to Mandate Tests, Chaos Injector, and API Dependencies.
- Verdict: Refuted (false)
- Priority: None
- Classification: n/a
- Recommendation: ignore

### F25 — PolicyEngine inferred edges (claim R25)
- Report claim: 19 INFERRED edges on `PolicyEngine` (examples: `CheckoutExecuteRequest`, `PolicyResult`) need verification.
- Verdict: Refuted (false)
- Priority: None
- Classification: leaked ordering
- Recommendation: ignore

### F26 — CatalogService inferred edges (claim R26)
- Report claim: 15 INFERRED edges on `CatalogService` (examples: `CatalogItem`, `CatalogResponse`) need verification.
- Verdict: Confirmed
- Priority: None
- Proof: `src/services/catalog.py:30`
- Classification: n/a
- Recommendation: ignore

### F27 — Vault inferred edges to MCP types (claim R27)
- Report claim: 9 INFERRED edges on `Vault` (examples: `MCPRequest`, `MCPResponse`) need verification.
- Verdict: Refuted (false)
- Priority: P3 (hygiene)
- Classification: n/a
- Recommendation: ignore

### F28 — Mandate inferred edges (claim R28)
- Report claim: 18 INFERRED edges on `Mandate` (examples: `MandateIdBody`, `PaymentExecutor`) need verification.
- Verdict: Confirmed
- Priority: None
- Proof: `src/services/executor.py:12`
- Classification: n/a
- Recommendation: ignore

## Ticket candidates

Formalized (F20 only). `/to-tickets` publish later, not in this task.

### T1 — Export the full Audit chain through `/audit/export`

- **Blocked by:** None (can start immediately)
- **Scope:** `GET /audit/export` returns the hash-chained Audit log and runs `AuditLogger.verify_chain`. Per-mandate `GET /audit/mandate/{mandate_id}` stays. No money-path change, no new store.
- **Acceptance:**
  - [ ] Export no longer returns `{"status": "stub", "entries": []}`
  - [ ] Export invokes `verify_chain`; a tampered chain fails closed
  - [ ] Existing per-mandate route and `tests/unit/test_audit.py` stay green

No other Confirmed non-dup finding is ticket-worthy. God-node degree and expected `Mandate` / `CatalogService` edges are domain hubs, not debt. Graph misreads (F14–F18, F21, F23–F25, F27) are extractor artifacts.

None of the report claims match a Known-Broken row (`_idempotency_keys`, `VaultError`→400, stale `docs/AGENTS.md`, junctions, duplicate rules, no CI, uv multipart, Python drift). Those stay registered in `docs/TROUBLESHOOTING.md` only.

## Registry updates

Proposed Known-Broken row (do not apply in this task):

| Item | Symptom | Status | Safe workaround |
|---|---|---|---|
| `/audit/export` stub | `GET /audit/export` returns `{"status": "stub", "entries": []}`; does not call `verify_chain` or `get_chain` | Known gap | Use `GET /audit/mandate/{mandate_id}` plus `AuditLogger.verify_chain` in-process |
