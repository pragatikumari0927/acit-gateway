# PHASES

**ACIT Gateway — 10-day build plan (26 August – 4 September 2026)**

Internal freeze: 4 September 2026; Google Form submit: 5 September 2026.

Prompt 8 numbering. Design docs (ARCHITECTURE.md, design.md, CONTEXT.md) are in place. Runtime `src/` implements C1–C7 plus v1 HTTP routes; tests live under `tests/`. Each phase must leave tests green. Do not skip.

### Phase 1: Foundation (Days 1‑2)
- Goals: Setup, C1 (Protocol Abstraction), C3 (Mandate Vault)
- Deliverables: Working parsers for AP2/TAP/P3P/UAP, agent registration, mandate storage, signature verification.
- Unit tests for C1 and C3.

#### Specific tasks with checkboxes and dependencies
- [x] Day 1 (26 Aug): Bootstrap/setup — pyproject.toml (Python 3.11+), requirements.txt, .gitignore, project layout confirmation
  - Depends on: none
- [x] Day 1: Implement C1 (Protocol Abstraction) — `src/models/mandate.py` (Pydantic Mandate/InternalMandate, OrderItem, Protocol enum)
  - Depends on: bootstrap
- [x] Day 1: Implement parsers in `src/services/protocol_parser.py` — `parse_envelope`, `parse_ap2`, `parse_tap`, `parse_p3p`, `parse_uap` (structure only → Mandate)
  - Depends on: C1 models
- [x] Day 1: Unit tests for C1 (valid + invalid envelopes, ProtocolParseError.reason_code)
  - Depends on: C1 parsers
- [x] Day 2 (27 Aug): Implement C3 (Mandate Vault) — `src/services/vault.py` (injected db_path, SQLite agents/mandates/denylist, register_agent, store_mandate, verify_signature, validate_mandate, revoke_mandate, is_denied, add_to_denylist)
  - Depends on: C1 (Mandate model)
- [x] Day 2: ES256 JWT support for signature verification (generate/verify keypairs and JWTs for agent identity)
  - Depends on: vault base
- [x] Day 2: Unit tests for C3 (agent registration, mandate storage/TTL/revocation/denylist, signature verification)
  - Depends on: C3 impl
- [x] Day 2: Run `pytest tests/unit -q` for Phase 1; all green
  - Depends on: all Phase 1 tasks

### Phase 2: Catalog & Firewall (Days 3‑4)
- Goals: C2 (Semantic Catalog), C4 (Prompt Firewall)
- Deliverables: Catalog API with static JSON data, IDPI detection and sanitisation.
- Unit tests for C2 and C4.

#### Specific tasks with checkboxes and dependencies
- [x] Day 3 (28 Aug): Implement C2 (Semantic Catalog) — `src/services/catalog.py` + static JSON data (agent-readable offers, CatalogItem model, lookup by SKU)
  - Depends on: Phase 1 (Mandate sku_allowlist usage)
- [x] Day 3: Unit tests for C2 (catalog queries, SKU allowlist matching)
  - Depends on: C2 impl
- [x] Day 4 (29 Aug): Implement C4 (Prompt Firewall) — `src/services/firewall.py` (deterministic IDPI / tool-poison detection + sanitisation on raw envelopes before parse)
  - Depends on: Phase 1 parser + Phase 2 catalog (for context)
- [x] Day 4: Unit tests for C4 (poisoned tool descriptions/schemas → sanitized or Refusal with reason_code)
  - Depends on: C4 impl
- [x] Day 4: Smoke integration between C2 and C4; confirm no LLM used anywhere
  - Depends on: C2 + C4
- [x] Day 4: Run Phase 2 unit tests; all green
  - Depends on: all Phase 2 tasks

### Phase 2.5: Policy, Money action, v1 routes (4 Sep 2026)
- Goals: C5 PolicyEngine, C7 ChaosInjector, Razorpay test-mode executor, FastAPI `/v1/*`
- Deliverables: Guardrails on Proposal, chaos at the Razorpay seam only, catalog/mandates/checkout/audit HTTP, 85 pytest passed.
- [x] C5 PolicyEngine — first-failure-wins: mandate_invalid, over_limit, sku_not_allowed, invented_price, invented_discount (percent bounds), dark_pattern
- [x] Vault.get_mandate (deserialize stored payload); AuditLogger.get_chain(mandate_id) without changing verify_chain()
- [x] C7 ChaosInjector(enabled, failure_rate, rng) — TimeoutError only for razorpay_create_order / razorpay_capture_payment
- [x] PaymentExecutor — razorpay.Client, TEST MODE keys only (`rzp_test_*`), capture off by default
- [x] DI in `src/api/dependencies.py` + routers under `src/api/routes/` registered at `/v1`
- [x] Integration tests with httpx.AsyncClient, tmp SQLite overrides, mocked executor; webhooks still unprefixed

### Phase 3: Policy & Execution (Days 5‑6)
- Goals: C5 (Policy Engine), C6 (Audit Logger), Razorpay Orders API integration.
- Deliverables: Deterministic policy engine, append‑only audit log, ability to create and capture orders.
- Unit and integration tests.

#### Specific tasks with checkboxes and dependencies
- [x] Day 5 (30 Aug): Implement C5 (Policy Engine) — `src/services/policy.py` (deterministic checks: Mandate bounds, catalog prices, Guardrails — no invented discounts, no false urgency, SKU/amount/TTL)
  - Depends on: Phase 2 (Catalog + Firewall clean)
- [x] Day 5: Unit tests for C5 (policy decisions, violation reason_codes, Refusal paths)
  - Depends on: C5 impl
- [x] Day 5: Implement C6 (Audit Logger) — `src/services/audit.py` (append-only SQLite, SHA-256 hash chain: `hash = sha256(prev_hash || payload)`)
  - Depends on: prior gates (firewall/parser/vault/policy)
- [x] Day 6 (31 Aug): Razorpay test-mode Orders API integration (adapter to create/capture orders using test-mode keys only; never real money)
  - Depends on: C5 policy green-light + injected client
- [x] Day 6: Unit + integration tests for policy engine, audit logger, Razorpay create/capture (temp SQLite, mocks for test-mode)
  - Depends on: Phase 3 impls
- [x] Day 6: Verify gating (Razorpay only after all prior passes) + every allow/Refusal writes Audit
  - Depends on: full Phase 3
- [x] Day 6: Run all Phase 3 tests (unit + integration); green
  - Depends on: all Phase 3 tasks

### Phase 4: Testing & Polish (Days 7‑8)
- Goals: C7 (Chaos Test), C8 (Dark‑Pattern Tests), full integration.
- Deliverables: Failure injection, retry logic, dark‑pattern test suite.
- All tests passing.

#### Specific tasks with checkboxes and dependencies
- [x] Day 7 (1 Sep): Implement C7 (Chaos Test) — `src/services/chaos.py` (failure injection harness: timeouts, 5xx, bad JSON, rate limits — **only** against Razorpay adapter)
  - Depends on: Phase 3 Razorpay integration
- [x] Day 7: Add retry logic + graceful degradation for injected failures (still produce Refusal + Audit)
  - Depends on: C7
- [x] Day 7: Unit/chaos tests for C7
  - Depends on: C7 + retry
- [x] Day 8 (2 Sep): Implement C8 (Dark‑Pattern Tests) suite (explicit tests exercising false urgency, invented discounts, confirm-shaming, "No means no" escalation prevention in policy/guardrails)
  - Depends on: Phase 3 C5 policy engine
- [x] Day 8: Full integration test suite (FastAPI edge + temp DB + test-mode Razorpay + chaos + dark patterns)
  - Depends on: all prior phases + C7/C8
- [x] Day 8: Run complete test matrix (`pytest tests/unit tests/integration tests/chaos -q`); fix until all green
  - Depends on: test implementations
- [x] Day 8: One graceful failure path (chaos → Refusal + verified Audit chain)
  - Depends on: full Phase 4

### Phase 5: Documentation & Submission (Days 9‑10)
- Goals: README, architecture diagram, API reference, 5‑minute demo video.
- Deliverables: Complete documentation, unlisted video, Google Form submission.

#### Specific tasks with checkboxes and dependencies
- [ ] Day 9 (3 Sep): Update README.md (setup, run `docker compose up`, test commands, Guardrails note, “test-mode only”)
  - Depends on: all code + tests green
- [ ] Day 9: Maintain architecture diagrams (Mermaid in ARCHITECTURE.md, pipeline, C1–C8)
  - Depends on: stable implementation
- [ ] Day 9: API reference / usage examples (from design + actual routes if present)
  - Depends on: docs + code
- [ ] Day 10 (4 Sep): Record 5-minute unlisted demo video (docker up, happy-path Mandate → order, Refusal paths, audit chain verification, one chaos failure)
  - Depends on: all docs + working system
- [ ] Day 10: Write “what broke at 2 AM” incident summary from actual run
  - Depends on: video + testing
- [ ] Day 10: Prepare + submit Google Form (video link, repo, incident note); final freeze checklist
  - Depends on: video + docs + all tests
- [ ] Day 10: Final verification — all phases tasks complete, tests green, docs up-to-date
  - Depends on: everything in Phase 5

**Dependencies summary across phases**: Phase N depends on Phase N-1 deliverables being complete and tests green. Never call Razorpay (C6 integration) unless C1–C5 (per user C labels) have passed. No LLM on any gate. Follow CONTEXT vocabulary everywhere.
