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
from src.models.proposal import CheckoutExecuteResult, PolicyResult, Proposal
from src.services.audit import AuditLogger
from src.services.checkout import run_execute
from src.services.executor import PaymentExecutor
from src.services.firewall import PromptFirewall
from src.services.policy import PolicyEngine
from src.services.vault import Vault

router = APIRouter()


class CheckoutExecuteRequest(BaseModel):
    proposal: Proposal
    protocol: str | None = None
    envelope: dict[str, Any] | None = None


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


@router.post("/checkout/execute", response_model=CheckoutExecuteResult)
async def execute_checkout(
    body: CheckoutExecuteRequest,
    firewall: PromptFirewall = Depends(get_firewall),
    vault: Vault = Depends(get_vault),
    policy: PolicyEngine = Depends(get_policy),
    executor: PaymentExecutor = Depends(get_executor),
    audit: AuditLogger = Depends(get_audit),
) -> CheckoutExecuteResult:
    """HTTP adapter for run_execute. Fail closed: Refusal never calls Razorpay."""
    return await run_execute(
        body.proposal,
        protocol=body.protocol,
        envelope=body.envelope,
        firewall=firewall,
        vault=vault,
        policy=policy,
        executor=executor,
        audit=audit,
    )
