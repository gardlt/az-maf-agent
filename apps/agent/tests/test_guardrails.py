import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from az_maf_agent.approval_ledger import ApprovalLedger, issue_fixture_approval
from az_maf_agent.core import LOCAL
from az_maf_agent.guardrails import (
    ControlPolicy,
    FixtureControlBackend,
    FixtureOperator,
    RunControls,
)
from az_maf_agent.model import Denied


@pytest.fixture
def safety(configured):
    settings = configured(input_usd_per_million=1.25, output_usd_per_million=10.0)
    policy = ControlPolicy.model_validate_json(Path("config/guardrail-policy.json").read_text())
    backend = FixtureControlBackend(policy)
    now = [1000.0]
    controls = RunControls(backend, settings, clock=lambda: now[0])
    return controls, FixtureOperator(backend), now


def start(controls, principal=LOCAL):
    run_id = str(uuid4())
    return controls.start(principal, run_id)


def test_shared_concurrency_and_restart_cannot_refill_budget(safety):
    controls, _, _ = safety
    first = start(controls)
    second = RunControls(controls.backend, controls.settings, controls.clock)
    next_run = start(second)
    with pytest.raises(Denied, match="shared_concurrency"):
        start(second)
    controls.gate(LOCAL, first["run_id"], first["epoch"], "model", count=500)
    controls.reconcile(LOCAL, first["run_id"], 1, 20)
    controls.finish(LOCAL, first["run_id"], first["epoch"], "completed")
    assert sum(float(v) for v in controls.backend._state["daily"].values()) > 0
    third = start(second)
    assert third["run_id"] != first["run_id"]
    assert controls.backend._state["runs"][first["run_id"]]["calls"] == 1
    assert controls.backend._state["runs"][next_run["run_id"]]["calls"] == 0


def test_atomic_daily_reservations_across_clients(safety, configured):
    controls, _, _ = safety
    settings = configured(
        input_usd_per_million=1.25, output_usd_per_million=10.0, limits={"daily_usd": 0.04}
    )
    clients = [RunControls(controls.backend, settings, controls.clock) for _ in range(2)]
    runs = [start(c) for c in clients]

    def reserve(index):
        try:
            clients[index].gate(LOCAL, runs[index]["run_id"], 1, "model", count=500)
            return "accepted"
        except Denied as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, range(2)))
    assert sorted(results) == ["accepted", "shared_daily_budget"]
    assert sum(r["calls"] for r in controls.backend._state["runs"].values()) == 1


def test_stop_persists_and_runtime_has_no_recovery_method(safety):
    controls, operator, _ = safety
    run = start(controls)
    operator.publish(1, stop=True)
    restarted = RunControls(controls.backend, controls.settings, controls.clock)
    with pytest.raises(Denied, match="global_stop"):
        start(restarted)
    with pytest.raises(Denied, match="global_stop"):
        controls.gate(LOCAL, run["run_id"], 1, "model")
    assert not hasattr(controls, "publish")
    with pytest.raises(Denied, match="explicit_recovery_required"):
        operator.publish(2, stop=False)
    operator.publish(2, stop=False, recover=True)
    with pytest.raises(Denied, match="policy_changed"):
        controls.gate(LOCAL, run["run_id"], 1, "model")
    assert start(restarted)["epoch"] == 3


def test_policy_rollback_is_fenced_across_restart(safety):
    controls, operator, _ = safety
    old = controls.backend.policy()
    operator.publish(1, disabled=["tool:get_movie"])
    controls.backend._policy = old
    restarted = RunControls(controls.backend, controls.settings, controls.clock)
    with pytest.raises(Denied, match="control_rollback"):
        start(restarted)


def test_disabled_capability_scope_and_lease_are_enforced(safety):
    controls, operator, now = safety
    operator.publish(1, disabled=["tool:get_movie"])
    run = start(controls)
    with pytest.raises(Denied, match="capability_disabled"):
        controls.gate(LOCAL, run["run_id"], 2, "tool:get_movie")
    with pytest.raises(Denied, match="run_not_found"):
        controls.gate(replace(LOCAL, user="someone-else"), run["run_id"], 2, "model")
    now[0] += 30
    with pytest.raises(Denied, match="run_lease_expired"):
        controls.gate(LOCAL, run["run_id"], 2, "model")


def test_policy_outage_and_audit_failure_deny_before_reservations(safety):
    controls, _, _ = safety
    run = start(controls)
    before = json.dumps(controls.backend._state, sort_keys=True)

    def unavailable(event):
        raise Denied("audit_unavailable")

    controls.backend.audit = unavailable
    with pytest.raises(Denied, match="audit_unavailable"):
        controls.gate(LOCAL, run["run_id"], 1, "model", count=500)
    assert json.dumps(controls.backend._state, sort_keys=True) == before
    controls.backend.available = False
    with pytest.raises(Denied, match="control_unavailable"):
        controls.gate(LOCAL, run["run_id"], 1, "model")


def test_lost_state_after_bootstrap_is_not_treated_as_fresh_quota(safety):
    # Cloud adapter separately rejects missing state instead of empty_state bootstrap.
    from az_maf_agent.guardrail_blob import SharedDocument

    with pytest.raises(ValueError):
        SharedDocument.model_validate(
            {"schema_version": 1, "runs": {}, "daily": {}, "receipts": {}}
        )


def test_approval_exact_arguments_single_use_receipt_and_catalog_forbidden(safety):
    controls, operator, now = safety
    run = start(controls)
    ledger = ApprovalLedger(controls)
    args = {"operation": "simulation:credit", "account_ref": "classroom", "units": 2}
    approval = issue_fixture_approval(operator, LOCAL, run["run_id"], args, now=now[0])
    with pytest.raises(Denied, match="approval_invalid"):
        ledger.execute(LOCAL, run["run_id"], 1, args | {"units": 3}, approval.approval_id)
    assert controls.backend._state["receipts"] == {}
    receipt = ledger.execute(LOCAL, run["run_id"], 1, args, approval.approval_id)
    assert receipt["units"] == 2
    with pytest.raises(Denied, match="approval_consumed"):
        ledger.execute(LOCAL, run["run_id"], 1, args, approval.approval_id)
    assert ledger.receipt(LOCAL, approval.approval_id) == receipt
    with pytest.raises(Denied, match="receipt_not_found"):
        ledger.receipt(replace(LOCAL, user="other"), approval.approval_id)
    with pytest.raises(Denied, match="action_forbidden"):
        ledger.display(
            LOCAL,
            run["run_id"],
            1,
            {"operation": "put_movie", "account_ref": "classroom", "units": 2},
        )


@pytest.mark.parametrize("cause", ["expiry", "reject", "cancel", "revoke"])
def test_approval_invalidation_never_commits(cause, safety):
    controls, operator, now = safety
    run = start(controls)
    args = {"operation": "simulation:credit", "account_ref": "classroom", "units": 1}
    approval = issue_fixture_approval(
        operator, LOCAL, run["run_id"], args, now=now[0], approve=cause != "reject", ttl=10
    )
    if cause == "expiry":
        now[0] += 10
    elif cause == "cancel":
        controls.cancel(LOCAL, run["run_id"])
    elif cause == "revoke":
        operator.publish(1, stop=True)
    with pytest.raises(Denied):
        ApprovalLedger(controls).execute(LOCAL, run["run_id"], 1, args, approval.approval_id)
    assert controls.backend._state["receipts"] == {}


def test_terminal_provider_rejection_uses_versioned_unknown_usage_receipt(safety):
    from az_maf_agent.guardrail_blob import SharedDocument

    controls, _, _ = safety
    run = start(controls)
    controls.gate(LOCAL, run["run_id"], 1, "model", count=500)
    before = controls.backend.snapshot()
    controls.reject(LOCAL, run["run_id"], 1, 400)
    after = controls.backend.snapshot()
    record = after["runs"][run["run_id"]]
    assert after["schema_version"] == 2
    assert record["call_receipts"] == {"1": None}
    assert record["actual_tokens"] == 0 and not record["unresolved"]
    assert after["daily"] == before["daily"]
    assert record["usd"] == before["runs"][run["run_id"]]["usd"]
    SharedDocument.model_validate(after)
    after["schema_version"] = 1
    with pytest.raises(ValueError, match="nullable usage"):
        SharedDocument.model_validate(after)
    controls.reconcile(LOCAL, run["run_id"], 1, 10)
    assert controls.backend.snapshot()["runs"][run["run_id"]]["actual_tokens"] == 10


def test_server_failure_cannot_be_misclassified_as_known_rejection(safety):
    controls, _, _ = safety
    run = start(controls)
    controls.gate(LOCAL, run["run_id"], 1, "model", count=500)
    with pytest.raises(Denied, match="provider_usage"):
        controls.reject(LOCAL, run["run_id"], 1, 503)
    record = controls.backend.snapshot()["runs"][run["run_id"]]
    assert record["unresolved"] and record["call_receipts"] == {}
