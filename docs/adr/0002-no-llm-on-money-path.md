---
status: accepted
---

# No LLM on the Money path

Firewall, Vault, Guardrails, Mandate verification, Razorpay calls, and audit hashing are deterministic code. Agents are clients of the Gateway, not a model we host.

**Why:** Track 01 requires every Money action to be bounded, gated, and explainable. An LLM in those gates is neither. Track 02 is defense-only IDPI prevention — pattern sanitization and schema checks, not a classifier we cannot bound. The evaluation criterion “AI judgment” is this refusal.

**Considered:** an LLM Firewall “to catch novel jailbreaks.” Rejected for the MVP: non-deterministic Refusal, extra cost (₹0), and the wrong kind of AI for gated money.
