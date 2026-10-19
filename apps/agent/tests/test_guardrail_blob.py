import copy
from types import SimpleNamespace

import pytest

from az_maf_agent.guardrail_blob import BlobControlBackend, SharedDocument
from az_maf_agent.guardrails import empty_state
from az_maf_agent.model import Denied


def backend_with_response(responses):
    backend = BlobControlBackend.__new__(BlobControlBackend)
    backend.state_store = SimpleNamespace()
    backend.state_url = "state"
    calls = []
    state = empty_state()

    def snapshot():
        return copy.deepcopy(state), '"fresh"'

    def request(store, method, url, **kwargs):
        calls.append(kwargs)
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result, {}, b""

    backend._snapshot = snapshot
    backend.request = request
    return backend, calls


def test_confirmed_precondition_failure_retries_against_fresh_state():
    backend, calls = backend_with_response([412, 201])
    transitions = []

    def transition(state):
        transitions.append(state["policy_epoch"])
        state["policy_epoch"] += 1
        return 2

    assert backend.transact(transition) == 2
    assert transitions == [1, 1]
    assert all(call["conditions"] == {"If-Match": '"fresh"'} for call in calls)
    assert all(
        SharedDocument.model_validate_json(call["content"]).policy_epoch == 2 for call in calls
    )


def test_uncertain_write_outcome_is_never_retried_or_refunded():
    backend, calls = backend_with_response([Denied("control_unavailable"), 201])
    with pytest.raises(Denied, match="control_unavailable"):
        backend.transact(lambda state: state.update(policy_epoch=2))
    assert len(calls) == 1


def test_malformed_transition_never_writes():
    backend, calls = backend_with_response([201])
    with pytest.raises(Denied, match="control_invalid"):
        backend.transact(lambda state: state.update(policy_epoch=0))
    assert calls == []
