---
name: error-handling
description: FastAPI exception handlers, domain errors, refusal patterns, validation, and graceful degradation for the gateway. Maps to ProtocolParseError, VaultError, etc.
---

# Error Handling

## Core approach in this project
- Domain errors carry `reason_code` (e.g. from ProtocolParseError, VaultError).
- HTTP layer (later) maps them to Refusal responses + Audit writes.
- No leaking internals to clients.
- FastAPI: use `HTTPException`, custom exception handlers, and `RequestValidationError`.

## Patterns
- Raise typed errors early (parse, identity, bounds, denylist, guardrails).
- Catch at the service boundary or route and convert to consistent response shape.
- Always produce Audit event on terminal Refusal.
- For chaos: injected failures should surface as expected Refusals.

## Recommended structure
```python
class ACITError(Exception):
    reason_code: str

# In FastAPI app
@app.exception_handler(ACITError)
async def acit_error_handler(request, exc):
    # write audit
    return JSONResponse(status_code=..., content={"refused": True, "reason": exc.reason_code})
```

## Testing
- Test that every error path writes an Audit row.
- Assert exact reason_code values in responses.
- Use `tdd-test-engineer` + `test-coverage`.

Use with `fastapi-templates`, `security-audit`, `python-expert`.
