import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from az_maf_agent.containment import (
    ContainmentStore,
    DetectionRule,
    GraphAgentDisabler,
    QuarantineReader,
)
from az_maf_agent.core import LOCAL
from az_maf_agent.guardrails import ControlPolicy, FixtureControlBackend, RunControls
from az_maf_agent.model import Denied

T, A, B, BP, APP = (str(uuid4()) for _ in range(5))


@pytest.fixture
def registry(tmp_path):
    clock = [1000.0]
    store = ContainmentStore(tmp_path / "containment.db", clock=lambda: clock[0])
    for agent in (A, B):
        store.register(T, agent, BP, APP)
    return store, clock


def test_threshold_dedup_isolation_and_restart(registry):
    store, clock = registry
    rule = DetectionRule(version="denied-v1", threshold=3, window_seconds=60, max_age_seconds=60)
    readers = {a: QuarantineReader(store.path, T, a) for a in (A, B)}
    for reader in readers.values():
        reader.check()
    first = str(uuid4())
    assert not store.signal(T, A, first, clock[0], rule)
    assert not store.signal(T, A, first, clock[0], rule)
    assert not store.signal(T, B, str(uuid4()), clock[0], rule)
    assert not store.signal(T, A, str(uuid4()), clock[0], rule)
    assert store.signal(T, A, str(uuid4()), clock[0], rule)
    with pytest.raises(Denied, match="agent_quarantined"):
        readers[A].check()
    readers[B].check()
    ContainmentStore(store.path)
    with pytest.raises(Denied, match="agent_quarantined"):
        QuarantineReader(store.path, T, A).check()


def test_unknown_stale_future_and_duplicate_registry_fail_closed(registry):
    store, _ = registry
    rule = DetectionRule(version="v1", threshold=1, window_seconds=60, max_age_seconds=60)
    for timestamp in (0, 1001, float("nan"), float("inf"), "1000"):
        with pytest.raises(Denied, match="signal_time"):
            store.signal(T, A, str(uuid4()), timestamp, rule)
    with pytest.raises(Denied, match="unknown_agent"):
        store.signal(T, str(uuid4()), str(uuid4()), 1000, rule)
    with pytest.raises(Denied, match="registry_conflict"):
        store.register(T, A, BP, str(uuid4()))
    with pytest.raises(ValueError, match="individual_agent"):
        store.register(T, BP, BP, APP)
    QuarantineReader(store.path, T, A).check()


def test_concurrent_manual_disable_is_idempotent_and_private(registry):
    store, _ = registry
    incident = str(uuid4())
    with ThreadPoolExecutor(max_workers=8) as workers:
        list(workers.map(lambda _: store.request_disable(T, A, incident), range(16)))
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT count(*) FROM incidents").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM audit").fetchone()[0] == 1
        assert db.execute("SELECT generation FROM agents WHERE agent=?", (A,)).fetchone()[0] == 2
    assert store.path.stat().st_mode & 0o077 == 0
    QuarantineReader(store.path, T, B).check()


def test_failure_preserves_quarantine_and_retry_is_durable(registry):
    store, clock = registry
    incident = str(uuid4())
    store.request_disable(T, A, incident)

    class Directory:
        calls = 0

        def disable(self, *args):
            assert args == (T, A, BP, APP)
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("private-provider-payload")

    directory = Directory()
    assert store.attempt_disable(T, A, incident, directory) == "containment_failed"
    with pytest.raises(Denied, match="retry_deferred"):
        store.attempt_disable(T, A, incident, directory)
    with pytest.raises(Denied, match="agent_quarantined"):
        QuarantineReader(store.path, T, A).check()
    clock[0] += 3
    restarted = ContainmentStore(store.path, clock=lambda: clock[0])
    assert restarted.attempt_disable(T, A, incident, directory) == "directory_disabled"
    assert restarted.attempt_disable(T, A, incident, directory) == "directory_disabled"
    assert directory.calls == 2
    with sqlite3.connect(store.path) as db:
        assert "private-provider-payload" not in repr(
            db.execute("SELECT * FROM incidents").fetchall()
        )
    # Directory disable is deliberately not labelled full resource containment.
    with pytest.raises(Denied, match="agent_quarantined"):
        QuarantineReader(store.path, T, A).check()


def test_missing_corrupt_and_generation_change_deny(tmp_path, registry):
    for path in (tmp_path / "absent.db", tmp_path / "corrupt.db"):
        if path.name.startswith("corrupt"):
            path.write_text("not a database")
        with pytest.raises(Denied, match="containment_unavailable"):
            QuarantineReader(path, T, A).check()
    store, _ = registry
    reader = QuarantineReader(store.path, T, A)
    reader.check()
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE agents SET generation=generation+1 WHERE agent=?", (A,))
    with pytest.raises(Denied, match="quarantine_generation"):
        reader.check()


def test_quarantine_fences_dispatch_and_preserves_accounting(registry, configured):
    store, _ = registry
    settings = configured(input_usd_per_million=1.25, output_usd_per_million=10.0)
    policy = ControlPolicy.model_validate_json(Path("config/guardrail-policy.json").read_text())
    backend = FixtureControlBackend(policy)
    controls = RunControls(backend, settings, quarantine=QuarantineReader(store.path, T, A))
    run_id = str(uuid4())
    run = controls.start(LOCAL, run_id)
    controls.gate(LOCAL, run_id, run["epoch"], "model", count=500)
    previous = backend.snapshot()
    store.request_disable(T, A, str(uuid4()))
    for action in (
        lambda: controls.gate(LOCAL, run_id, run["epoch"], "model", count=500),
        lambda: controls.gate(LOCAL, run_id, run["epoch"]),
        lambda: controls.start(LOCAL, str(uuid4())),
    ):
        with pytest.raises(Denied, match="agent_quarantined"):
            action()
    assert backend.snapshot() == previous


@pytest.mark.parametrize("bad", ["type", "agent", "blueprint", "app", "enabled", "redirect"])
def test_graph_refuses_wrong_target_before_write(bad):
    requests = []
    payload = {
        "id": A,
        "appId": APP,
        "agentIdentityBlueprintId": BP,
        "@odata.type": "#microsoft.graph.agentIdentity",
        "accountEnabled": True,
    }
    field = {
        "type": "@odata.type",
        "agent": "id",
        "blueprint": "agentIdentityBlueprintId",
        "app": "appId",
        "enabled": "accountEnabled",
    }
    if bad in field:
        payload[field[bad]] = "invalid"

    def handler(request):
        requests.append(request)
        return httpx.Response(302 if bad == "redirect" else 200, json=payload)

    credential = SimpleNamespace(get_token=lambda _: SimpleNamespace(token="private-token"))
    adapter = GraphAgentDisabler(
        T, credential, http=httpx.Client(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(Denied):
        adapter.disable(T, A, BP, APP)
    assert len(requests) == 1 and requests[0].method == "GET"
    adapter.close()


def test_graph_disables_exact_agent_and_verifies_readback():
    requests = []
    enabled = [True]

    def handler(request):
        requests.append(request)
        assert (
            str(request.url)
            == f"https://graph.microsoft.com/v1.0/servicePrincipals/{A}/microsoft.graph.agentIdentity"
        )
        if request.method == "PATCH":
            assert request.content == b'{"accountEnabled":false}'
            enabled[0] = False
            return httpx.Response(204)
        return httpx.Response(
            200,
            json={
                "id": A,
                "appId": APP,
                "agentIdentityBlueprintId": BP,
                "@odata.type": "#microsoft.graph.agentIdentity",
                "accountEnabled": enabled[0],
            },
        )

    credential = SimpleNamespace(get_token=lambda _: SimpleNamespace(token="private-token"))
    adapter = GraphAgentDisabler(
        T, credential, http=httpx.Client(transport=httpx.MockTransport(handler))
    )
    adapter.disable(T, A, BP, APP)
    assert [r.method for r in requests] == ["GET", "PATCH", "GET"]
    adapter.disable(T, A, BP, APP)
    assert [r.method for r in requests][-2:] == ["GET", "GET"]
    adapter.close()


async def test_supervisor_cancels_active_work_after_quarantine(registry, configured):
    import asyncio

    from az_maf_agent.supervisor import SafetySupervisor

    store, _ = registry
    policy = ControlPolicy.model_validate_json(Path("config/guardrail-policy.json").read_text())
    policy = policy.model_copy(update={"poll_seconds": 0.01})
    backend = FixtureControlBackend(policy)
    controls = RunControls(backend, configured(), quarantine=QuarantineReader(store.path, T, A))
    supervisor = SafetySupervisor(controls)
    with pytest.raises(Denied, match="agent_quarantined"):
        async with supervisor.run(LOCAL):
            store.request_disable(T, A, str(uuid4()))
            await asyncio.sleep(1)
    assert next(iter(backend.snapshot()["runs"].values()))["status"] == "cancelled"
    await supervisor.close()


@pytest.mark.parametrize("failure", ["patch", "readback", "timeout"])
def test_unverified_graph_disable_never_passes(failure):
    calls = []

    def handler(request):
        calls.append(request.method)
        if request.method == "PATCH":
            if failure == "timeout":
                raise httpx.ReadTimeout("private-response", request=request)
            return httpx.Response(403 if failure == "patch" else 204)
        return httpx.Response(
            200,
            json={
                "id": A,
                "appId": APP,
                "agentIdentityBlueprintId": BP,
                "@odata.type": "#microsoft.graph.agentIdentity",
                "accountEnabled": True,
            },
        )

    credential = SimpleNamespace(get_token=lambda _: SimpleNamespace(token="private-token"))
    adapter = GraphAgentDisabler(
        T, credential, http=httpx.Client(transport=httpx.MockTransport(handler))
    )
    with pytest.raises((Denied, httpx.ReadTimeout)):
        adapter.disable(T, A, BP, APP)
    assert calls[:2] == ["GET", "PATCH"]
    adapter.close()


def test_late_failure_cannot_overwrite_newer_verified_disable(registry):
    from threading import Event

    store, clock = registry
    incident = str(uuid4())
    store.request_disable(T, A, incident)
    entered, release = Event(), Event()

    class DelayedFailure:
        def disable(self, *args):
            entered.set()
            assert release.wait(5)
            raise RuntimeError("late-private-error")

    class Success:
        def disable(self, *args):
            pass

    with ThreadPoolExecutor(max_workers=1) as worker:
        first = worker.submit(store.attempt_disable, T, A, incident, DelayedFailure())
        assert entered.wait(5)
        clock[0] += 31
        assert store.attempt_disable(T, A, incident, Success()) == "directory_disabled"
        release.set()
        assert first.result() == "directory_disabled"
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT state FROM incidents").fetchone()[0] == "directory_disabled"
        assert (
            db.execute("SELECT count(*) FROM audit WHERE action='containment_failed'").fetchone()[0]
            == 0
        )
