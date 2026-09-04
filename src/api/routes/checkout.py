"""Checkout propose (policy only) and execute (gated Money action)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.dependencies import (
    get_audit,
    get_executor,
    get_firewall,
    get_policy,
    get_vault,
)
from src.models.proposal import PolicyResult, Proposal
from src.services.audit import AuditLogger
from src.services.executor import PaymentExecutor
from src.services.firewall import PromptFirewall
from src.services.policy import PolicyEngine
from src.services.protocol_parser import parse_envelope
from src.services.vault import Vault

router = APIRouter()


class CheckoutExecuteRequest(BaseModel):
    proposal: Proposal
    protocol: str | None = None
    envelope: dict[str, Any] | None = None


async def _audit_refusal(
    audit: AuditLogger,
    action: str,
    proposal: Proposal,
    reason_code: str,
) -> None:
    await audit.log_entry(
        {
            "action": action,
            "outcome": "refusal",
            "agent_id": None,
            "mandate_id": proposal.mandate_id,
            "metadata_json": json.dumps({"reason_code": reason_code}),
        }
    )


@router.post("/checkout/propose", response_model=PolicyResult)
async def propose(
    proposal: Proposal,
    policy: PolicyEngine = Depends(get_policy),
    audit: AuditLogger = Depends(get_audit),
) -> PolicyResult:
    """Evaluate Guardrails only. No Money action."""
    result = await policy.evaluate_proposal(proposal)
    await audit.log_entry(
        {
            "action": "checkout.propose",
            "outcome": "ok" if result.allowed else "refusal",
            "mandate_id": proposal.mandate_id,
            "metadata_json": json.dumps({"reason_code": result.reason_code}),
        }
    )
    return result


@router.post("/checkout/execute")
async def execute_checkout(
    body: CheckoutExecuteRequest,
    firewall: PromptFirewall = Depends(get_firewall),
    vault: Vault = Depends(get_vault),
    policy: PolicyEngine = Depends(get_policy),
    executor: PaymentExecutor = Depends(get_executor),
    audit: AuditLogger = Depends(get_audit),
) -> dict[str, Any]:
    """Firewall → Parser (if envelope) → Vault/Policy → Executor → Audit.

    Fail closed: Firewall Refusal writes Audit and never calls Razorpay.
    """
    proposal = body.proposal
    if body.envelope is not None:
        ok, cleaned, reason = firewall.sanitize(body.envelope)
        if not ok:
            await _audit_refusal(audit, "checkout.execute", proposal, reason or "idpi_detected")
            return {"allowed": False, "reason_code": reason or "idpi_detected"}
        if body.protocol:
            parse_envelope(body.protocol, cleaned or body.envelope)

    result = await policy.evaluate_proposal(proposal)
    if not result.allowed:
        await _audit_refusal(
            audit, "checkout.execute", proposal, result.reason_code or "mandate_invalid"
        )
        return result.model_dump()

    mandate = await vault.get_mandate(proposal.mandate_id)
    if mandate is None:
        await _audit_refusal(audit, "checkout.execute", proposal, "mandate_invalid")
        return {
            "allowed": False,
            "reason_code": "mandate_invalid",
            "mandate_id": proposal.mandate_id,
        }

    try:
        payment = executor.execute(mandate, proposal)
    except Exception as exc:  # chaos / adapter failure — fail closed
        await _audit_refusal(audit, "checkout.execute", proposal, "executor_failure")
        return {
            "allowed": False,
            "reason_code": "executor_failure",
            "detail": type(exc).__name__,
        }

    await audit.log_entry(
        {
            "action": "checkout.execute",
            "outcome": "ok",
            "mandate_id": proposal.mandate_id,
            "agent_id": mandate.agent_id,
        }
    )
    return {"allowed": True, "reason_code": None, "payment": payment}
