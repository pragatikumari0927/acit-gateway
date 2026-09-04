"""Agent identity presented at the API seam (C3).

`issuer` and `status` are API-only: AgentRow persists agent_id, public_key_pem,
and created_at only. Do not treat these extra fields as stored columns.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AgentIdentity(BaseModel):
    """Registered Agent as seen by the API."""

    agent_id: str
    public_key_pem: str
    registered_at: datetime
    issuer: str | None = None
    status: Literal["active", "revoked", "suspended"] = "active"
