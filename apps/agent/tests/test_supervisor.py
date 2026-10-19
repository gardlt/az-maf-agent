import asyncio
import json
from pathlib import Path

import pytest
from test_model_tools import MovieClient, ToolTransport, tool_call

from az_maf_agent.core import LOCAL, Service
from az_maf_agent.guardrails import (
    ControlPolicy,
    FixtureControlBackend,
    FixtureOperator,
    RunControls,
)
from az_maf_agent.model import Denied
from az_maf_agent.supervisor import SafetySupervisor


def supervisor(settings):
    policy = ControlPolicy.model_validate_json(Path("config/guardrail-policy.json").read_text())
    policy = policy.model_copy(update={"poll_seconds": 0.01})
    backend = FixtureControlBackend(policy)
    return SafetySupervisor(RunControls(backend, settings)), FixtureOperator(backend)


async def test_shared_model_accounting_and_reconciliation_integrated(configured):
    settings = configured(input_usd_per_million=1.25, output_usd_per_million=10.0)
    safety, _ = supervisor(settings)
    transport = ToolTransport(
        [tool_call(), ({"role": "assistant", "content": "A movie."}, "stop", 30)]
    )
    service = Service(
        settings,
        transport,
        movie_client=MovieClient(),
        movie_model_tools=True,
        safety=safety,
        audit=lambda _: None,
    )
    sid = service.create(LOCAL)["session_id"]
    response = await service.chat(LOCAL, sid, "Find a movie", 0)
    state = safety.controls.backend._state["runs"][response["run_id"]]
    assert state["calls"] == 2 and state["tools"] == 1
    assert state["actual_tokens"] == 50 and state["call_receipts"] == {"1": 20, "2": 30}
    assert not state["unresolved"] and state["status"] == "completed"
    assert json.loads(json.dumps(safety.controls.backend.events))
    await service.close()


async def test_global_stop_cancels_uncooperative_provider_and_suppresses_late_history(configured):
    settings = configured(
        input_usd_per_million=1.25, output_usd_per_million=10.0, limits={"per_user_parallel": 1}
    )
    safety, operator = supervisor(settings)
    entered, release = asyncio.Event(), asyncio.Event()

    class Uncooperative(ToolTransport):
        async def complete_tool_turn(self, messages, settings):
            entered.set()
            try:
                await release.wait()
            except asyncio.CancelledError:
                await release.wait()
            return {"role": "assistant", "content": "Late response"}, "stop", 20

    service = Service(
        settings,
        Uncooperative([]),
        movie_client=MovieClient(),
        movie_model_tools=True,
        safety=safety,
        audit=lambda _: None,
    )
    sid = service.create(LOCAL)["session_id"]
    task = asyncio.create_task(service.chat(LOCAL, sid, "Work", 0))
    await asyncio.wait_for(entered.wait(), 2)
    operator.publish(1, stop=True)
    with pytest.raises(Denied, match="global_stop"):
        await asyncio.wait_for(task, 2)
    state = next(iter(safety.controls.backend._state["runs"].values()))
    assert state["status"] == "cancelled" and state["unresolved"]
    assert service.sessions[sid].revision == 0
    operator.publish(2, stop=False, recover=True)
    with pytest.raises(Denied, match="shared_concurrency"):
        await service.chat(LOCAL, sid, "Cannot replace unresolved work", 0)
    release.set()
    for _ in range(100):
        await asyncio.sleep(0.01)
        if not next(iter(safety.controls.backend._state["runs"].values()))["unresolved"]:
            break
    assert not next(iter(safety.controls.backend._state["runs"].values()))["unresolved"]
    assert service.sessions[sid].revision == 0
    assert not service.sessions[sid].state.state.get("stage1_history", {}).get("messages")
    await service.close()


async def test_component_disable_denies_before_actual_mcp_dispatch(configured):
    settings = configured(input_usd_per_million=1.25, output_usd_per_million=10.0)
    safety, operator = supervisor(settings)
    operator.publish(1, disabled=["tool:get_movie"])
    movie = MovieClient()
    service = Service(
        settings,
        ToolTransport([tool_call()]),
        movie_client=movie,
        movie_model_tools=True,
        safety=safety,
        audit=lambda _: None,
    )
    sid = service.create(LOCAL)["session_id"]
    with pytest.raises(Denied, match="capability_disabled"):
        await service.chat(LOCAL, sid, "Find a movie", 0)
    assert movie.calls == []
    assert service.sessions[sid].revision == 0
    await service.close()


async def test_unknown_pricing_blocks_before_provider_call(settings):
    safety, _ = supervisor(settings)
    transport = ToolTransport([])
    service = Service(
        settings,
        transport,
        movie_client=MovieClient(),
        movie_model_tools=True,
        safety=safety,
        audit=lambda _: None,
    )
    sid = service.create(LOCAL)["session_id"]
    with pytest.raises(Denied, match="unknown_pricing"):
        await service.chat(LOCAL, sid, "No billable dispatch", 0)
    assert transport.messages == []
    await service.close()
