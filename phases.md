# Phases

Prompt 8 “Phase 1” is C1 + C3. Remaining work follows `AGENTS.md`.

## Phase 1 — Foundation (this prompt)

**C1 — Mandate + parser**

- `src/models/mandate.py` — `Mandate` (`InternalMandate` alias), `OrderItem`, `Protocol`
- `src/services/protocol_parser.py` — AP2, TAP, P3P, UAP → `Mandate`
- Unit tests: valid and invalid envelopes

**C3 — Vault**

- SQLite: `agents`, `mandates`, `denylist` in `src/services/vault.py`
- `register_agent`, `store_mandate`, `verify_signature`, `validate_mandate`, `revoke_mandate`, `is_denied`, `add_to_denylist`
- JWT ES256 in `src/utils/crypto.py`
- Unit tests for Vault

## Later (do not skip ahead)

3. Firewall (IDPI / tool-poison)
4. Guardrails / policy
5. Catalog
6. Razorpay test-mode adapter
7. Hash-chained audit
8. Chaos + one graceful failure
9. Public README, video, “what broke at 2 AM”
