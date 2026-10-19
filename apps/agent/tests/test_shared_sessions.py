import asyncio
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from test_model_tools import MovieClient, ToolTransport, tool_call

from az_maf_agent.core import LOCAL, Service
from az_maf_agent.guardrails import ControlPolicy, FixtureControlBackend, RunControls
from az_maf_agent.model import Denied
from az_maf_agent.shared_sessions import FixtureSessionBackend, SessionRepository
from az_maf_agent.supervisor import SafetySupervisor


def replicas(settings, transports):
    policy = ControlPolicy.model_validate_json(Path("config/guardrail-policy.json").read_text())
    controls = FixtureControlBackend(policy.model_copy(update={"poll_seconds": 0.01}))
    sessions = FixtureSessionBackend()
    return [
        Service(
            settings,
            t,
            movie_client=MovieClient(),
            movie_model_tools=True,
            safety=SafetySupervisor(RunControls(controls, settings)),
            session_repository=SessionRepository(sessions, settings),
            audit=lambda _: None,
        )
        for t in transports
    ]


async def test_history_and_counters_resume_on_another_replica_and_reset_preserves_usage(configured):
    settings = configured(input_usd_per_million=1.25, output_usd_per_million=10.0)
    transports = [
        ToolTransport(
            [tool_call(), ({"role": "assistant", "content": "First answer"}, "stop", 20)]
        ),
        ToolTransport([({"role": "assistant", "content": "Second answer"}, "stop", 20)]),
    ]
    first, second = replicas(settings, transports)
    sid = (await first.create_async(LOCAL))["session_id"]
    await first.chat(LOCAL, sid, "First question", 0)
    response = await second.chat(LOCAL, sid, "Second question", 1)
    assert response["revision"] == 2
    assert any(m["content"] == "First question" for m in transports[1].messages[0])
    assert second.sessions[sid].movie_reads == 1
    assert (await second.reset_async(LOCAL, sid))["revision"] == 3
    doc = first.session_repository.load(LOCAL, sid)
    assert doc["messages"] == [] and doc["movie_reads"] == 1
    assert sum(float(v) for v in first.safety.controls.backend._state["daily"].values()) > 0
    with pytest.raises(Denied, match="stale_revision"):
        await first.chat(LOCAL, sid, "Old revision", 2)
    await first.close()
    await second.close()


async def test_duplicate_and_concurrent_writes_cannot_dispatch_or_resurrect_after_remote_reset(
    configured,
):
    settings = configured(input_usd_per_million=1.25, output_usd_per_million=10.0)
    entered, release = asyncio.Event(), asyncio.Event()

    class Paused(ToolTransport):
        async def complete_tool_turn(self, messages, settings):
            entered.set()
            await release.wait()
            return {"role": "assistant", "content": "Old history"}, "stop", 20

    first, second = replicas(settings, [Paused([]), ToolTransport([])])
    sid = (await first.create_async(LOCAL))["session_id"]
    task = asyncio.create_task(first.chat(LOCAL, sid, "Paused", 0))
    await asyncio.wait_for(entered.wait(), 2)
    with pytest.raises(Denied, match="busy"):
        await second.chat(LOCAL, sid, "Concurrent", 0)
    await second.reset_async(LOCAL, sid)
    release.set()
    with pytest.raises((Denied, asyncio.CancelledError)):
        await asyncio.wait_for(task, 2)
    doc = second.session_repository.load(LOCAL, sid)
    assert doc["revision"] == 1 and doc["messages"] == []
    assert not second.transport.messages
    await first.close()
    await second.close()


def test_expiry_and_cross_owner_lookup_do_not_disclose_or_recreate(settings):
    now = [1000.0]
    repository = SessionRepository(FixtureSessionBackend(), settings, clock=lambda: now[0])
    sid = str(uuid4())
    repository.create(LOCAL, sid)
    with pytest.raises(Denied, match="session_not_found"):
        repository.load(replace(LOCAL, user="another-user"), sid)
    now[0] += settings.limits.idle_seconds
    with pytest.raises(Denied, match="session_not_found"):
        repository.load(LOCAL, sid)
    with pytest.raises(Denied, match="session_not_found"):
        repository.claim(LOCAL, sid, 0, str(uuid4()))


async def test_global_session_capacity_survives_replica_change(configured):
    settings = configured(
        input_usd_per_million=1.25, output_usd_per_million=10.0, limits={"max_sessions": 1}
    )
    first, second = replicas(settings, [ToolTransport([]), ToolTransport([])])
    await first.create_async(LOCAL)
    with pytest.raises(Denied, match="session_capacity"):
        await second.create_async(LOCAL)
    await first.close()
    await second.close()
