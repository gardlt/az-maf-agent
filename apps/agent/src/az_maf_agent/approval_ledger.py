"""A synthetic credit ledger, explicitly separate from movie catalog permissions."""

import hashlib
import json
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .guardrails import scope_ref
from .model import Denied


class CreditArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    operation: Literal["simulation:credit"]
    account_ref: Literal["classroom"]
    units: int = Field(ge=1, le=10)


def argument_ref(arguments):
    return hashlib.sha256(arguments.model_dump_json().encode()).hexdigest()


class Approval(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    approval_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    run_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    scope_ref: str = Field(pattern=r"^[0-9a-f]{64}$")
    epoch: int = Field(ge=1)
    argument_ref: str = Field(pattern=r"^[0-9a-f]{64}$")
    issued_at: float = Field(ge=0, allow_inf_nan=False)
    expires_at: float = Field(ge=0, allow_inf_nan=False)
    approver_ref: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: Literal["approve", "reject"]


def issue_fixture_approval(operator, principal, run_id, arguments, *, approve=True, now, ttl=60):
    """Fixture operator only; hosted approval uses an independently authorized writer."""
    if not 0 < ttl <= 60:
        raise Denied("approval_invalid")
    arguments = CreditArguments.model_validate(arguments)
    policy = operator.backend.policy()
    owner = scope_ref(principal)
    run = operator.backend._state["runs"].get(run_id)
    if (
        not run
        or run["owner"] != owner
        or run["epoch"] != policy.epoch
        or run["status"] != "active"
        or run["cancelled"]
        or now >= run["deadline"]
    ):
        raise Denied("approval_invalid")
    approval = Approval(
        approval_id=str(uuid.uuid4()),
        run_id=run_id,
        scope_ref=owner,
        epoch=policy.epoch,
        argument_ref=argument_ref(arguments),
        issued_at=float(now),
        expires_at=float(min(now + ttl, run["deadline"])),
        approver_ref=hashlib.sha256(b"fixture-operator").hexdigest(),
        decision="approve" if approve else "reject",
    )
    operator.backend._approvals[approval.approval_id] = approval.model_dump_json().encode()
    return approval


class ApprovalLedger:
    def __init__(self, controls):
        self.controls = controls

    def display(self, principal, run_id, epoch, arguments):
        try:
            arguments = CreditArguments.model_validate(arguments)
        except ValueError:
            raise Denied("action_forbidden") from None
        self.controls.gate(principal, run_id, epoch, "simulation:credit")
        return {
            "consequence": "Synthetic classroom credits only; no external transfer or catalog write",
            "arguments": arguments.model_dump(),
            "argument_ref": argument_ref(arguments),
            "run_id": run_id,
            "epoch": epoch,
            "scope_ref": scope_ref(principal),
        }

    def execute(self, principal, run_id, epoch, arguments, approval_id):
        display = self.display(principal, run_id, epoch, arguments)
        try:
            approval = Approval.model_validate_json(
                self.controls.backend.read_approval(approval_id)
            )
        except ValueError:
            raise Denied("approval_invalid") from None
        now = self.controls.clock()
        if (
            approval.decision != "approve"
            or approval.approval_id != approval_id
            or approval.run_id != run_id
            or approval.scope_ref != display["scope_ref"]
            or approval.epoch != epoch
            or approval.argument_ref != display["argument_ref"]
            or not approval.issued_at <= now < approval.expires_at
            or approval.expires_at - approval.issued_at > 60
        ):
            raise Denied("approval_invalid")
        self.controls._event(
            "simulated_action_authorized", run_id, epoch, capability="simulation:credit"
        )

        def transition(state):
            committed_at = self.controls.clock()
            if not approval.issued_at <= committed_at < approval.expires_at:
                raise Denied("approval_invalid")
            self.controls._active(state, run_id, display["scope_ref"], epoch, committed_at)
            # Approval consumption and this fixture's effect/receipt are one transaction.
            # A lost response is reconciled through receipt(), never a blind redispatch.
            if approval_id in state["receipts"]:
                raise Denied("approval_consumed")
            if len(state["receipts"]) >= 1000:
                raise Denied("control_capacity")
            receipt = {
                "receipt_id": str(uuid.uuid4()),
                "approval_id": approval_id,
                "argument_ref": display["argument_ref"],
                "scope_ref": display["scope_ref"],
                "run_id": run_id,
                "epoch": epoch,
                "units": display["arguments"]["units"],
                "time": committed_at,
                "status": "committed",
            }
            state["receipts"][approval_id] = receipt
            return receipt

        self.controls._authority(epoch, "simulation:credit")
        return self.controls.backend.transact(transition)

    def receipt(self, principal, approval_id):
        owner = scope_ref(principal)

        def transition(state):
            receipt = state["receipts"].get(approval_id)
            if not receipt or receipt["scope_ref"] != owner:
                raise Denied("receipt_not_found")
            return json.loads(json.dumps(receipt))

        return self.controls.backend.transact(transition)
