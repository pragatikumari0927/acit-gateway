# ACIT Gateway

The inbound bridge that turns a bounded Agent Mandate into a Razorpay test-mode payment, or a Refusal. This glossary is the ubiquitous language for issues, tests, and code.

## Language

### Actors

**ACIT Gateway**:
The bridge that accepts a Protocol envelope from any Agent, verifies the Mandate, and either executes a Money action or issues a Refusal.
_Avoid_: proxy, MCP server, Razorpay plugin, chatbot

**Agent**:
A software actor that presents a Protocol envelope on behalf of a User. Not the human.
_Avoid_: bot, assistant, LLM, client (when we mean the actor)

**User**:
The human who authorised the Mandate.
_Avoid_: customer, buyer, account (those names belong to the Merchant’s shopper)

**Merchant**:
The Razorpay test-mode seller whose Catalog and Guardrails the Gateway enforces.
_Avoid_: vendor, shop, payee

**Customer**:
The Merchant’s shopper — the person or organisation being charged in the Money action. Often the same human as the User, but not the same role.

### Mandate and protocols

**Mandate**:
A User-authorised spend envelope: max amount, SKU allow-list, TTL, and Agent identity. The Gateway’s only canonical internal object for “may this Agent pay?”
_Avoid_: intent, prompt, order, permission slip, consent blob

**Protocol envelope**:
The on-the-wire payload (AP2, P3P, TAP, or UAP) before it becomes a Mandate.
_Avoid_: request body, webhook, mandate (until parsed)

**AP2**:
Agent Payments Protocol — the Google / FIDO open protocol for agent-performed payments (v0.2). One inbound Protocol envelope shape.

**P3P**:
Pine Labs Payments Protocol — a live HTTP-native agent payment protocol on UPI Reserve Pay, one-time mandates, and cards. One inbound Protocol envelope shape.

**UAP**:
NPCI Unified Agent Protocol — the in-development Indian standard for registering and authorising Agents on UPI. One inbound Protocol envelope shape.

**TAP**:
An inbound Protocol envelope type named by this project. Do not expand the acronym in code or docs until a public spec is cited.

### Trust and security

**Vault**:
The store of Agent identity material (keys, JWT claims) used as cryptographic proof of who acted.
_Avoid_: secrets manager, keychain, auth service

**Firewall**:
The Gateway’s deterministic inbound sanitizer for IDPI and MCP tool poisoning. Not an LLM.
_Avoid_: WAF, filter, moderator, guard (that word is Guardrail)

**IDPI**:
Indirect Prompt Injection, including MCP tool poisoning — hidden instructions in tool descriptions, schemas, or envelope fields that try to hijack the Agent.
_Avoid_: using IDPI as a Razorpay product name; “jailbreak” as the domain term

**Guardrail**:
A Merchant policy the Gateway enforces before any Money action: no invented discounts, no false urgency, SKU / amount / TTL bounds.
_Avoid_: rule, filter, firewall (Firewall is IDPI sanitization)

### Commerce

**Catalog**:
The agent-readable list of offers the Merchant actually sells.
_Avoid_: inventory, menu, product feed (unless we mean a source that feeds the Catalog)

**Money action**:
Creating or capturing a Razorpay test-mode payment. Always bounded, gated, and explainable.
_Avoid_: charge, checkout, transaction (too vague — say Money action or name the Razorpay object)

### Outcomes

**Audit event**:
An append-only record of a Gateway decision or Money action, hash-chained with SHA-256.
_Avoid_: log line, trace, webhook payload

**Refusal**:
A completed Gateway outcome that does not execute a Money action, with a coded reason. A success mode, not an error.
_Avoid_: error, exception, failure (when the Mandate was correctly rejected)
