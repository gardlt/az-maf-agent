"""Separate Azure CLI operator; never imported by the runtime API."""

import argparse
import hashlib
import json
import re
import subprocess
import time
import uuid
from pathlib import Path

from azure.identity import AzureCliCredential

from .guardrail_blob import BlobControlBackend, SharedDocument
from .guardrails import CAPABILITIES, ControlPolicy, empty_state
from .model import Denied


class BlobOperator:
    def __init__(self, backend, clock=time.time, actor_ref=None):
        self.backend = backend
        self.clock = clock
        self.actor_ref = actor_ref

    def _audit(self, event):
        if self.actor_ref is not None:
            event["operator_ref"] = self.actor_ref
        self.backend.audit(event)

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
        self._audit({"event": "operator_bootstrap", "epoch": 1, "time": self.clock()})
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
        self._audit(
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
        self._audit(
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

    def reconcile_contained(self, run_id, expected_epoch, evidence):
        """Operator accepts unknown usage after platform containment; never refunds."""
        policy = self.backend.policy()
        now = self.clock()
        resources = evidence.get("resources", [])
        if (
            not self.actor_ref
            or not re.fullmatch(r"[0-9a-f]{64}", self.actor_ref)
            or not policy.global_stop
            or policy.epoch != expected_epoch
            or evidence.get("account") != self.backend.account
            or type(evidence.get("observed_at")) not in (int, float)
            or not 0 <= now - evidence["observed_at"] <= 30
            or not resources
        ):
            raise Denied("containment_evidence_required")
        for resource in resources:
            revisions = resource.get("revisions", [])
            if (
                not resource.get("id")
                or not revisions
                or any(
                    row.get("active") is not False
                    or row.get("replicas") != 0
                    or row.get("running") != "Stopped"
                    for row in revisions
                )
            ):
                raise Denied("containment_evidence_required")
        digest = hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()
        self._audit(
            {
                "event": "operator_unknown_contained",
                "run_id": run_id,
                "epoch": expected_epoch,
                "time": now,
                "evidence_ref": digest,
                "status": "contained_unknown_usage",
            }
        )

        def transition(state):
            run = state["runs"].get(run_id)
            if state["policy_epoch"] != expected_epoch or not run or not run["unresolved"]:
                raise Denied("reconciliation_conflict")
            run["operator_resolution"] = "contained_unknown_usage"
            run["unresolved"] = False
            run["status"] = "cancelled"
            return {
                "run_id": run_id,
                "resolution": run["operator_resolution"],
                "reserved_tokens": run["tokens"],
                "reserved_usd": run["usd"],
                "actual_tokens": run["actual_tokens"],
                "evidence_ref": digest,
            }

        return self.backend.transact(transition)


def platform_evidence(account, resource_group, subscription):
    def az(*args):
        completed = subprocess.run(
            ["az", *args, "--subscription", subscription, "-o", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(completed.stdout)

    apps = az("containerapp", "list", "-g", resource_group)
    resources = []
    for app in apps:
        containers = app["properties"]["template"]["containers"]
        matching = any(
            {entry["name"]: entry.get("value") for entry in container.get("env", [])}.get(
                "CONTROL_ACCOUNT"
            )
            == account
            for container in containers
        )
        if not matching:
            continue
        rows = az(
            "containerapp", "revision", "list", "-g", resource_group, "-n", app["name"], "--all"
        )
        resources.append(
            {
                "id": app["id"],
                "revisions": [
                    {
                        "name": row["name"],
                        "active": row["properties"]["active"],
                        "replicas": row["properties"].get("replicas"),
                        "running": row["properties"].get("runningState"),
                    }
                    for row in rows
                ],
            }
        )
    return {"account": account, "observed_at": time.time(), "resources": resources}


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
    command = sub.add_parser("reconcile-contained")
    command.add_argument("--run-id", required=True)
    command.add_argument("--expected-epoch", type=int, required=True)
    command.add_argument("--resource-group", required=True)
    command.add_argument("--subscription", required=True)
    command.add_argument("--evidence-output", type=Path, required=True)
    args = parser.parse_args()
    backend = BlobControlBackend(args.account, credential=AzureCliCredential())
    actor_ref = None
    if args.action != "status":
        actor = subprocess.run(
            ["az", "ad", "signed-in-user", "show", "--query", "id", "-o", "tsv"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        uuid.UUID(actor)
        actor_ref = hashlib.sha256(actor.encode()).hexdigest()
    operator = BlobOperator(backend, actor_ref=actor_ref)
    try:
        if args.action == "status":
            policy = backend.policy()
        elif args.action == "bootstrap":
            policy = operator.bootstrap()
        elif args.action in ("approve", "reject"):
            policy = operator.approve(
                args.run_id,
                {"operation": "simulation:credit", "account_ref": "classroom", "units": args.units},
                actor_ref,
                reject=args.action == "reject",
            )
        elif args.action == "reconcile-contained":
            evidence = platform_evidence(args.account, args.resource_group, args.subscription)
            args.evidence_output.parent.mkdir(parents=True, exist_ok=True)
            args.evidence_output.write_text(json.dumps(evidence, indent=2) + "\n")
            policy = operator.reconcile_contained(args.run_id, args.expected_epoch, evidence)
        else:
            options = {args.action: getattr(args, "capability", True)}
            policy = operator.publish(args.expected_epoch, **options)
        print(
            json.dumps(
                policy.model_dump() if hasattr(policy, "model_dump") else policy, sort_keys=True
            )
        )
    finally:
        backend.close()


if __name__ == "__main__":
    main()
