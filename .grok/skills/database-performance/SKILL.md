---
name: database-performance
description: SQLite performance, connection pooling, indexing, query patterns, and monitoring for the gateway's Vault, mandates, denylist, and audit store.
---

# Database Performance (SQLite focus)

Current implementation: direct sqlite3 in Vault, injected db_path. Keep it simple.

## Guidelines
- Use WAL mode for concurrent reads during writes.
- Prepared statements / parameterized queries only.
- Minimal indexes on agent_id, mandate_id, expiry, revoked.
- Keep transactions short; commit after audit append.
- For tests: file DB or :memory: with proper isolation.
- Monitor with EXPLAIN QUERY PLAN on slow paths (audit append, denylist checks, mandate lookup).

## Common wins
- Index on (agent_id, revoked, expires_at)
- Batch audit writes where safe (but preserve hash chain order)
- Connection per operation or short-lived pooled (avoid long-lived in async without care)
- Vacuum + analyze in maintenance (not hot path)

## When to consider SQLAlchemy or other
Only after clear measurement showing direct sqlite is the bottleneck. See `python-sqlalchemy`.

## Verification
- Add targeted tests for hot queries.
- Use with `performance-optimizer` + `test-coverage`.
- In chaos: measure under injected load / slow IO.

See `python-expert` for connection hygiene.
