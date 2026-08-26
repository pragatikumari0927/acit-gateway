# Rules

Authoritative copies live in `AGENTS.md` and `CONTEXT.md`. This file is the short checklist Prompt 8 refers to.

- Type hints on public functions. Docstrings on public modules and methods.
- Pydantic v2 at model seams. No untyped dicts as Mandates.
- Names from `CONTEXT.md`: Mandate, Protocol envelope, Agent, Vault, Refusal. `InternalMandate` is an alias of `Mandate`.
- No LLM in Firewall, Vault, Guardrails, Mandate verification, Money actions, or audit hashing.
- Tests hit service interfaces, not SQL rows or private helpers.
- A Refusal (or `ProtocolParseError` / `VaultError` until HTTP exists) is a coded outcome, not a bare exception.
- Parser checks structure. Vault checks identity, expiry, revocation, denylist. Guardrails come later.
