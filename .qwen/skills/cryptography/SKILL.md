---
name: cryptography
description: Cryptography, JWT/ES256, signature verification, secure practices for the ACIT gateway (Vault, mandates, audit). Complements security-audit.
---

# Cryptography (Defense Only)

This project uses ES256 (from earlier crypto.py) for agent signatures and JWTs.

## Guidelines
- Prefer cryptography library over PyJWT raw where possible for low-level.
- Always verify signatures with public key; never trust claims without `verify_jwt`.
- Use constant-time comparisons.
- Rotate/revoke via denylist + TTL on mandates.
- Never log keys, nonces, or full JWTs in production paths.
- For test-mode only: no real key material in source.

## Common Patterns Here
- `Vault.verify_signature(...)`
- Mandate JWT validation with expiry + scope checks.
- Audit event hashing (when phase 7 arrives).

Use `security-audit` for any change touching keys, signing, or verification.
See also superpowers for rigorous review.
