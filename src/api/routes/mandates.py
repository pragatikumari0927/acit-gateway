"""Mandate Vault routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.dependencies import get_vault
from src.models.mandate import Mandate
from src.services.vault import Vault, VaultError

router = APIRouter()


class MandateIdBody(BaseModel):
    mandate_id: str


@router.post("/mandates/validate")
async def validate_mandate(
    body: MandateIdBody,
    vault: Vault = Depends(get_vault),
) -> dict[str, bool | str]:
    """Check whether a Mandate is currently valid (TTL, revocation, denylist)."""
    valid = await vault.validate_mandate(body.mandate_id)
    return {"mandate_id": body.mandate_id, "valid": valid}


@router.post("/mandates/store")
async def store_mandate(
    mandate: Mandate,
    vault: Vault = Depends(get_vault),
) -> dict[str, str]:
    """Persist a Mandate. Revoked ids cannot be overwritten."""
    try:
        await vault.store_mandate(mandate)
    except VaultError as exc:
        raise HTTPException(status_code=400, detail=exc.reason_code) from exc
    return {"mandate_id": mandate.mandate_id}


@router.get("/mandates/{mandate_id}")
async def read_mandate(
    mandate_id: str,
    vault: Vault = Depends(get_vault),
) -> Mandate:
    """Return a stored Mandate payload."""
    mandate = await vault.get_mandate(mandate_id)
    if mandate is None:
        raise HTTPException(status_code=404, detail="mandate_not_found")
    return mandate
