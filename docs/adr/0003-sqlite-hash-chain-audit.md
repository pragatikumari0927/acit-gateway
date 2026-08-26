---
status: accepted
---

# SQLite plus a SHA-256 hash chain for Audit events

Audit events are append-only SQLite rows. Each row stores `hash = sha256(prev_hash || payload)`. The chain is the integrity proof we demo (Track 01 audit trail, Track 02 IDPI Refusal evidence).

**Considered:** Postgres + transactional outbox; an external log store. Rejected — ₹0, single process, 10-day MVP. Swapping the database later does not change the Mandate or the hash rule.

Do not update or delete Audit events. Chaos must not rewrite history.
