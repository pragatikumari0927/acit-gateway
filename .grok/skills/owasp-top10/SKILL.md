---
name: owasp-top10
description: OWASP Top 10 (2021) mapping and mitigations for API-first Python services. Focused on the risks relevant to agentic payment gateways.
---

# OWASP Top 10 for the ACIT Gateway

Relevant items and controls:

- A01 Broken Access Control: Mandate verification + scope/TTL/denylist in Vault before action.
- A02 Cryptographic Failures: ES256 only, proper verify_jwt, no weak algos, key rotation via denylist.
- A03 Injection: Strict Protocol parsing, Pydantic validation, no SQL string concat (use params), IDPI sanitizer.
- A04 Insecure Design: Defense-only (no offense tooling), explicit Refusals, audit everything.
- A05 Security Misconfiguration: No debug in prod paths, least privilege, env-only secrets.
- A06 Vulnerable Components: Dependabot + pip-audit/safety in CI (github-actions).
- A07 Identification/Auth Failures: Signature-based agent identity, no session cookies for agents.
- A08 Software/Data Integrity: Hash-chained audit (future), signed mandates.
- A09 Logging/Monitoring Failures: Structured safe logs + full Audit trail.
- A10 SSRF: No arbitrary outbound from parser/vault/firewall; only controlled Razorpay test client.

## Usage
Run `security-audit` on any change touching auth, crypto, input, or money paths.
Combine with `cryptography`, `fastapi-security`, `production-readiness`.

Reference current OWASP for updates but prioritize the project's threat model (agent envelopes, test money, IDPI defense).
