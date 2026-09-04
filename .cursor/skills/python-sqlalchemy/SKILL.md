---
name: python-sqlalchemy
description: SQLAlchemy 2.0 patterns, ORM vs Core, async, migrations, testing, and when to prefer raw sqlite for simple services like the ACIT gateway.
---

# Python SQLAlchemy

Project note: The gateway currently uses Python stdlib sqlite3 directly in Vault (injected db_path). Use this skill when discussing or adding SQLAlchemy.

## When to use SQLAlchemy here
- For complex queries, relationships, or when scaling beyond single-file mandates/audit.
- Keep Alembic for migrations if introduced.
- Prefer async SQLAlchemy (SQLAlchemy 2.0 + asyncpg or aiosqlite) for FastAPI.

## Key Patterns
- Use `Mapped` + `mapped_column` (2.0 style).
- Session / engine injection, never global in services.
- For tests: use in-memory or file-backed test DB, scope per test.
- Hybrid properties for computed mandate fields.

## Testing
```python
from sqlalchemy import create_engine, text
engine = create_engine("sqlite:///:memory:")
```

## With this project
- Do not introduce SQLAlchemy until Guardrails or later phases unless a clear need.
- See Vault for current direct sqlite usage.
- Combine with `python-expert` + `test-coverage`.

Prefer the simplest working approach per project constraints.
