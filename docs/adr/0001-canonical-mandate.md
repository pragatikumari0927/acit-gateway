---
status: accepted
---

# Canonical Mandate as the only internal spend object

Inbound Protocols (AP2, P3P, TAP, UAP) differ on the wire. We parse each Protocol envelope into one Mandate (max amount, SKU allow-list, TTL, Agent identity) and run Vault, Guardrails, Razorpay, and Audit against that object only.

**Considered:** a payment engine per protocol. Rejected — four Money-action paths would duplicate gates and make Track 01’s “bounded, gated, explainable” bar unverifiable.

Adapters live in the parser. They do not call Razorpay.
