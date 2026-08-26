# Memory

## 2026-08-26 — Phase 1 Day 1 (C1)

- Bootstrap: `pyproject.toml`, `requirements.txt`, `.gitignore`.
- `Mandate` / `InternalMandate`, `OrderItem`, `Protocol` in `src/models/mandate.py`.
- Parsers for AP2, TAP, P3P, UAP in `src/services/protocol_parser.py`.
- `pytest tests/unit/test_protocol_parser.py` — 13 passed.
- Added `rules.md` and `phases.md` (were missing; Prompt 8 referred to them).

## 2026-08-26 — Phase 1 Day 2 (C3)

- ES256 JWT in `src/utils/crypto.py` (`generate_es256_keypair`, `sign_jwt`, `verify_jwt`).
- Vault SQLite schema: `agents`, `mandates`, `denylist`.
- `register_agent`, `store_mandate`, `verify_signature`, `validate_mandate`, `revoke_mandate`, `is_denied`, `add_to_denylist`.
- `pytest tests/unit` — 26 passed (13 parser + 3 crypto + 10 vault).
