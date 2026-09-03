---
name: test-coverage
description: Pytest coverage, mocking strategies, test quality, and measuring coverage for Python/FastAPI projects. Use when adding tests, debugging low coverage, or improving test suites.
---

# Test Coverage

Use together with `tdd-test-engineer` and `python-expert`.

## Core Commands
- `pytest --cov=app --cov-report=term-missing --cov-report=html`
- `pytest --cov=app --cov-fail-under=80`
- `coverage html` then open htmlcov/index.html

## Best Practices
- Aim for high branch coverage on critical paths (auth, payments, money flows).
- Use `pytest-mock` or `unittest.mock` for external services (Razorpay, DB in some tests).
- Prefer targeted unit tests over broad integration for speed.
- Mark slow/chaos tests: `@pytest.mark.slow` or `@pytest.mark.chaos`.
- Exclude generated code, migrations, and vendor in .coveragerc.

## Mocking Patterns
```python
from unittest.mock import AsyncMock, patch

async def test_razorpay_call(mocker):
    m = mocker.patch("app.services.razorpay.create_order", new_callable=AsyncMock)
    m.return_value = {"id": "order_123"}
    ...
```

## When Coverage Drops
1. Run the narrow test first.
2. Use `tdd-test-engineer` to write the missing case.
3. Re-measure.

See also: superpowers test-driven-development skill.
