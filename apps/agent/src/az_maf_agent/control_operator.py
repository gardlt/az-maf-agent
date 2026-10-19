"""Separate Azure CLI operator; never imported by the runtime API."""

import argparse
import hashlib
import json
import time
import uuid

from azure.identity import AzureCliCredential

from .guardrail_blob import BlobControlBackend, SharedDocument
from .guardrails import CAPABILITIES, ControlPolicy, empty_state
from .model import Denied


class BlobOperator:
    def __init__(self, backend, clock=time.time):
        self.backend = backend
        self.clock = clock

    def bootstrap(self):
        backend = self.backend
        # Both objects must be absent. Missing established state is never repaired
        # automatically: that would erase outstanding spend and unknown effects.
        for store, url in (
            (backend.policy_store, backend.policy_url),
            (backend.state_store, backend.state_url),
        ):
            status, headers, _ = backend.request(store, "GET", url)
            if status != 404 or headers.get("x-ms-error-code") != "BlobNotFound":
                raise Denied("bootstrap_requires_empty_store")
        policy = ControlPolicy(
            schema_version=1,
            epoch=1,
            global_stop=True,
            disabled=[],
            poll_seconds=2.0,
            containment_seconds=10.0,
            lease_seconds=30.0,
            audit_retention_days=30,
            violation_limit=3,
        )
        backend.audit({"event": "operator_bootstrap", "epoch": 1, "time": self.clock()})
        # Policy is stopped before state is created; a partial bootstrap stays closed.
        for store, url, payload in (
            (backend.policy_store, backend.policy_url, policy.model_dump_json().encode()),
            (
                backend.state_store,
                backend.state_url,
                SharedDocument.model_validate(empty_state()).model_dump_json().encode(),
            ),
        ):
            status, _, _ = backend.request(
                store, "PUT", url, content=payload, conditions={"If-None-Match": "*"}
            )
            if status != 201:
                raise Denied("bootstrap_incomplete")
        return policy

    def publish(self, expected_epoch, *, stop=False, recover=False, disable=None, enable=None):
        backend = self.backend
        status, headers, body = backend.request(backend.policy_store, "GET", backend.policy_url)
        if status != 200:
            raise Denied("control_unavailable")
        policy = ControlPolicy.model_validate_json(body)
        etag = backend.etag(headers)
        if policy.epoch != expected_epoch:
            raise Denied("policy_conflict")
        if sum((stop, recover, disable is not None, enable is not None)) != 1:
            raise Denied("operator_action_invalid")
        disabled = set(policy.disabled)
        if disable is not None:
            if disable not in CAPABILITIES:
                raise Denied("capability_invalid")
            disabled.add(disable)
        if enable is not None:
            if enable not in CAPABILITIES:
                raise Denied("capability_invalid")
            disabled.discard(enable)
        backend.audit(
            {
                "event": "operator_policy_change",
                "epoch": expected_epoch,
                "time": self.clock(),
                "status": "requested",
            }
        )

        def fence(state):
            # Separate blobs are not one transaction. Advance the state floor first:
            # interruption or a losing policy CAS causes denial, never stale dispatch.
            epoch = max(state["policy_epoch"], policy.epoch) + 1
            state["policy_epoch"] = epoch
            return epoch

        epoch = backend.transact(fence)
        updated = ControlPolicy.model_validate(
            {
                **policy.model_dump(),
                "epoch": epoch,
                "disabled": sorted(disabled),
                "global_stop": False if recover else (True if stop else policy.global_stop),
            }
        )
        status, _, _ = backend.request(
            backend.policy_store,
            "PUT",
            backend.policy_url,
            content=updated.model_dump_json().encode(),
            conditions={"If-Match": etag},
        )
        if status != 201:
            raise Denied("policy_publish_incomplete")
        return updated

    def approve(self, run_id, arguments, approver_ref, *, reject=False):
        from .approval_ledger import Approval, CreditArguments, argument_ref

        arguments = CreditArguments.model_validate(arguments)
        policy = self.backend.policy()
        state = self.backend.snapshot()
        now = float(self.clock())
        run = state["runs"].get(run_id)
        if (
            policy.global_stop
            or "simulation:credit" in policy.disabled
            or state["policy_epoch"] != policy.epoch
            or not run
            or run["epoch"] != policy.epoch
            or run["status"] != "active"
            or run["cancelled"]
            or now >= min(run["deadline"], run["lease_until"])
        ):
            raise Denied("approval_invalid")
        approval = Approval(
            approval_id=str(uuid.uuid4()),
            run_id=run_id,
            scope_ref=run["owner"],
            epoch=policy.epoch,
            argument_ref=argument_ref(arguments),
            issued_at=now,
            expires_at=min(now + 60, run["deadline"], run["lease_until"]),
            approver_ref=approver_ref,
            decision="reject" if reject else "approve",
        )
        self.backend.audit(
            {
                "event": "operator_approval",
                "run_id": run_id,
                "epoch": policy.epoch,
                "time": now,
                "status": "requested",
            }
        )
        status, _, _ = self.backend.request(
            self.backend.policy_store,
            "PUT",
            self.backend.base(self.backend.policy_store)
            + "approvals/"
            + approval.approval_id
            + ".json",
            content=approval.model_dump_json().encode(),
            conditions={"If-None-Match": "*"},
        )
        if status != 201:
            raise Denied("approval_publish_incomplete")
        return approval


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account", required=True)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status")
    sub.add_parser("bootstrap")
    for action in ("stop", "recover", "disable", "enable"):
        command = sub.add_parser(action)
        command.add_argument("--expected-epoch", type=int, required=True)
        if action in ("disable", "enable"):
            command.add_argument("capability", choices=sorted(CAPABILITIES))
    for action in ("approve", "reject"):
        command = sub.add_parser(action)
        command.add_argument("--run-id", required=True)
        command.add_argument("--units", required=True, type=int, choices=range(1, 11))
    args = parser.parse_args()
    backend = BlobControlBackend(args.account, credential=AzureCliCredential())
    operator = BlobOperator(backend)
    try:
        if args.action == "status":
            policy = backend.policy()
        elif args.action == "bootstrap":
            policy = operator.bootstrap()
        elif args.action in ("approve", "reject"):
            import subprocess

            actor = subprocess.run(
                ["az", "ad", "signed-in-user", "show", "--query", "id", "-o", "tsv"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            uuid.UUID(actor)
            policy = operator.approve(
                args.run_id,
                {"operation": "simulation:credit", "account_ref": "classroom", "units": args.units},
                hashlib.sha256(actor.encode()).hexdigest(),
                reject=args.action == "reject",
            )
        else:
            options = {args.action: getattr(args, "capability", True)}
            policy = operator.publish(args.expected_epoch, **options)
        print(json.dumps(policy.model_dump(), sort_keys=True))
    finally:
        backend.close()


if __name__ == "__main__":
    main()
