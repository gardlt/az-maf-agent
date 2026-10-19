"""Operator publication must fail closed between the two Blob transactions."""

import json
from types import SimpleNamespace

import pytest

from az_maf_agent.control_operator import BlobOperator
from az_maf_agent.guardrails import ControlPolicy, empty_state
from az_maf_agent.model import Denied


class Backend:
    def __init__(self):
        self.policy_store = SimpleNamespace()
        self.state_store = SimpleNamespace()
        self.policy_url = "policy"
        self.state_url = "state"
        self.documents = {}
        self.state = empty_state()
        self.events = []
        self.fail_publish = False

    def request(self, store, method, url, **kwargs):
        if method == "GET":
            if url not in self.documents:
                return 404, {"x-ms-error-code": "BlobNotFound"}, b""
            return 200, {"etag": '"one"'}, self.documents[url]
        if self.fail_publish and url == "policy":
            return 412, {}, b""
        if kwargs["conditions"].get("If-None-Match") == "*" and url in self.documents:
            return 412, {}, b""
        self.documents[url] = kwargs["content"]
        return 201, {}, b""

    def etag(self, headers):
        return headers["etag"]

    def audit(self, event):
        self.events.append(event)

    def transact(self, transition):
        return transition(self.state)


def test_bootstrap_stopped_and_never_overwrites_existing_state():
    backend = Backend()
    operator = BlobOperator(backend)
    assert operator.bootstrap().global_stop
    assert json.loads(backend.documents["state"])["daily"] == {}
    with pytest.raises(Denied, match="bootstrap_requires_empty_store"):
        operator.bootstrap()


def test_lost_policy_publication_preserves_higher_state_fence():
    backend = Backend()
    operator = BlobOperator(backend)
    operator.bootstrap()
    backend.fail_publish = True
    with pytest.raises(Denied, match="policy_publish_incomplete"):
        operator.publish(1, recover=True)
    assert backend.state["policy_epoch"] == 2
    assert ControlPolicy.model_validate_json(backend.documents["policy"]).global_stop
    backend.fail_publish = False
    recovered = operator.publish(1, recover=True)
    assert recovered.epoch == 3 and not recovered.global_stop


def test_recovery_preserves_disabled_components_and_requires_exact_epoch():
    backend = Backend()
    operator = BlobOperator(backend)
    operator.bootstrap()
    assert operator.publish(1, disable="model").global_stop
    recovered = operator.publish(2, recover=True)
    assert recovered.disabled == ["model"]
    with pytest.raises(Denied, match="policy_conflict"):
        operator.publish(2, enable="model")


def test_operator_approval_is_bound_to_current_live_run_and_arguments():
    from az_maf_agent.approval_ledger import Approval, CreditArguments, argument_ref

    backend = Backend()
    operator = BlobOperator(backend, clock=lambda: 100.0)
    operator.bootstrap()
    operator.publish(1, recover=True)
    backend.policy = lambda: ControlPolicy.model_validate_json(backend.documents["policy"])
    backend.snapshot = lambda: backend.state
    backend.base = lambda store: ""
    run_id = "b166e493-ac24-4cdc-a76e-aa4e040f02ba"
    backend.state["runs"][run_id] = {
        "owner": "a" * 64,
        "epoch": 2,
        "status": "active",
        "cancelled": False,
        "deadline": 220.0,
        "lease_until": 130.0,
    }
    arguments = CreditArguments(operation="simulation:credit", account_ref="classroom", units=3)
    approval = operator.approve(run_id, arguments, "b" * 64)
    stored = Approval.model_validate_json(
        backend.documents["approvals/" + approval.approval_id + ".json"]
    )
    assert stored.argument_ref == argument_ref(arguments)
    assert stored.scope_ref == "a" * 64
    assert stored.expires_at == 130.0
    backend.state["runs"][run_id]["cancelled"] = True
    with pytest.raises(Denied, match="approval_invalid"):
        operator.approve(run_id, arguments, "b" * 64)
