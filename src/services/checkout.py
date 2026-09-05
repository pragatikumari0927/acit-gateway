"""Money-action execute: Firewall → parsed Mandate → Guardrails → Vault → Razorpay → Audit.

One public interface. The HTTP adapter stays thin. No LLM.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from src.models.proposal import CheckoutExecuteResult, Proposal
from src.services.audit import AuditLogger
from src.services.executor import PaymentExecutor
from src.services.firewall import PromptFirewall
from src.services.policy import PolicyEngine
from src.services.protocol_parser import ProtocolParseError, parse_envelope
from src.services.vault import Vault


def _refuse(mandate_id: str, reason_code: str) -> CheckoutExecuteResult:
    return CheckoutExecuteResult(
        mandate_id=mandate_id,
        allowed=False,
        reason_code=reason_code,
        violations=[reason_code],
        payment=None,
    )


async def _audit_refusal(
    audit: AuditLogger,
    proposal: Proposal,
    reason_code: str,
    agent_id: str | None = None,
) -> None:
    await audit.log_entry(
        {
            "action": "checkout.execute",
            "outcome": "refusal",
            "agent_id": agent_id,
            "mandate_id": proposal.mandate_id,
            "metadata_json": json.dumps({"reason_code": reason_code}),
        }
    )


async def run_execute(
    proposal: Proposal,
    *,
    protocol: str | None,
    envelope: dict[str, Any] | None,
    firewall: PromptFirewall,
    vault: Vault,
    policy: PolicyEngine,
    executor: PaymentExecutor,
    audit: AuditLogger,
) -> CheckoutExecuteResult:
    """Gate a Money action. Fail closed: any Refusal writes Audit and skips Razorpay."""
    parsed_mandate_id = proposal.mandate_id

    if envelope is not None:
        ok, cleaned, reason = firewall.sanitize(envelope)
        if not ok:
            code = reason or "idpi_detected"
            await _audit_refusal(audit, proposal, code)
            return _refuse(proposal.mandate_id, code)
        if not protocol:
            await _audit_refusal(audit, proposal, "unknown_protocol")
            return _refuse(proposal.mandate_id, "unknown_protocol")
        try:
            parsed = parse_envelope(protocol, cleaned or envelope)
        except ProtocolParseError as exc:
            await _audit_refusal(audit, proposal, exc.reason_code)
            return _refuse(proposal.mandate_id, exc.reason_code)
        if parsed.mandate_id != proposal.mandate_id:
            await _audit_refusal(audit, proposal, "mandate_invalid")
            return _refuse(proposal.mandate_id, "mandate_invalid")
        parsed_mandate_id = parsed.mandate_id

    result = await policy.evaluate_proposal(proposal)
    if not result.allowed:
        code = result.reason_code or "mandate_invalid"
        await _audit_refusal(audit, proposal, code)
        return CheckoutExecuteResult(
            mandate_id=result.mandate_id,
            allowed=False,
            reason_code=code,
            violations=result.violations or [code],
            payment=None,
        )

    mandate = await vault.get_mandate(parsed_mandate_id)
    if mandate is None:
        await _audit_refusal(audit, proposal, "mandate_invalid")
        return _refuse(proposal.mandate_id, "mandate_invalid")

    try:
        payment = await asyncio.to_thread(executor.execute, mandate, proposal)
    except Exception:  # noqa: BLE001 — fail-closed: any executor fault is a Refusal, never a 500
        await _audit_refusal(audit, proposal, "executor_failure", agent_id=mandate.agent_id)
        return _refuse(proposal.mandate_id, "executor_failure")

    await audit.log_entry(
        {
            "action": "checkout.execute",
            "outcome": "ok",
            "mandate_id": proposal.mandate_id,
            "agent_id": mandate.agent_id,
        }
    )
    return CheckoutExecuteResult(
        mandate_id=proposal.mandate_id,
        allowed=True,
        reason_code=None,
        violations=[],
        payment=payment,
    )
