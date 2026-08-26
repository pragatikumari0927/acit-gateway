# Memory

## 2026-08-26 — Phase 1 Day 1 (C1)

- Bootstrap: `pyproject.toml`, `requirements.txt`, `.gitignore`.
- `Mandate` / `InternalMandate`, `OrderItem`, `Protocol` in `src/models/mandate.py`.
- Parsers for AP2, TAP, P3P, UAP in `src/services/protocol_parser.py`.
- `pytest tests/unit/test_protocol_parser.py` — 13 passed.
- Added `rules.md` and `phases.md` (were missing; Prompt 8 referred to them).
