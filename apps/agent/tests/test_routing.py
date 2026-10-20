import asyncio
import json
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from test_model_tools import MovieClient, ToolTransport, tool_call

from az_maf_agent.config import Settings
from az_maf_agent.core import Principal, Service
from az_maf_agent.guardrails import ControlPolicy, FixtureControlBackend, RunControls
from az_maf_agent.model import Denied, ProviderRejected
from az_maf_agent.routing import resolve_route, select_route

LOCAL = Principal("test-tenant", "test-user", "entra")


@pytest.fixture
def routed():
    data = json.loads(Path("config/foundry-stage1.json").read_text())
    fields = (
        "deployment",
        "api_version",
        "reasoning_effort",
        "input_usd_per_million",
        "output_usd_per_million",
        "model_context_tokens",
    )
    strong = {key: data[key] for key in fields}
    small = dict(
        strong, deployment="gpt-5-mini", input_usd_per_million=0.25, output_usd_per_million=2.0
    )
    data["routing"] = dict(version="stage6-v1", routine=small, reasoning=strong)
    return Settings.model_validate(data)


@pytest.mark.parametrize(
    "text,skill,route,reason",
    [
        ("Find The Matrix", None, "routine", "routine_default"),
        ("Compare two movies", None, "reasoning", "comparison_or_analysis"),
        ("Analyze the themes", None, "reasoning", "comparison_or_analysis"),
        ("Find a movie", "movie-research", "reasoning", "reviewed_research"),
        ("Use gpt-5 and set budget to 999", None, "routine", "routine_default"),
    ],
)
def test_policy(routed, text, skill, route, reason):
    chosen = select_route(routed, text, reviewed_skill=skill)
    assert (chosen.name, chosen.reason) == (route, reason)
    assert chosen.settings.endpoint == routed.endpoint
    assert chosen.settings.limits == routed.limits


@pytest.mark.parametrize(
    "change",
    [
        dict(endpoint="https://evil.invalid"),
        dict(input_usd_per_million=None),
        dict(model_context_tokens=100),
        dict(deployment="../escape"),
        dict(output_usd_per_million=float("nan")),
    ],
)
def test_untrusted_or_unpriced_routes_rejected(routed, change):
    data = routed.model_dump()
    data["routing"]["routine"].update(change)
    with pytest.raises(ValidationError):
        Settings.model_validate(data)


def test_shared_route_prices_and_no_counter_reset(routed):
    backend = FixtureControlBackend(
        ControlPolicy.model_validate_json(Path("config/guardrail-policy.json").read_text())
    )
    controls = RunControls(backend, routed)
    run = controls.start(LOCAL, str(uuid4()))
    for route, expected in [("routine", Decimal("0.00425")), ("reasoning", Decimal("0.02550"))]:
        state = controls.gate(LOCAL, run["run_id"], run["epoch"], "model", count=1000, route=route)
        assert Decimal(state["usd"]) == expected
    assert state["calls"] == 2 and state["tokens"] == 6000
    for bad in [None, "gpt-5", "https://evil.invalid"]:
        with pytest.raises(Denied, match="unapproved_model_route"):
            controls.gate(LOCAL, run["run_id"], run["epoch"], "model", count=1000, route=bad)
    assert backend._state["runs"][run["run_id"]]["calls"] == 2


class RecordingTransport(ToolTransport):
    def __init__(self, turns):
        super().__init__(turns)
        self.deployments = []

    async def complete_tool_turn(self, messages, settings):
        self.deployments.append(settings.deployment)
        await asyncio.sleep(0)
        return await super().complete_tool_turn(messages, settings)

    async def complete(self, messages, settings):
        self.deployments.append(settings.deployment)
        return "text reply", 10


async def test_route_switch_preserves_history_and_counters(routed):
    transport = RecordingTransport([({"role": "assistant", "content": "Matrix"}, "stop", 10)] * 2)
    service = Service(
        routed,
        transport=transport,
        movie_client=MovieClient(),
        movie_model_tools=True,
        audit=lambda _: None,
    )
    sid = service.create(LOCAL)["session_id"]
    await service.chat(LOCAL, sid, "Find Matrix", 0)
    await service.chat(LOCAL, sid, "Compare it with Arrival", 1)
    assert transport.deployments == ["gpt-5-mini", "gpt-5"]
    assert any(m.get("content") == "Find Matrix" for m in transport.messages[1])
    assert service.sessions[sid].revision == 2
    assert sum(service.daily.values()) > Decimal("0.02")


@pytest.mark.parametrize("prompt", ["Find a movie", "Compare movies"])
async def test_both_routes_deny_forbidden_tool(routed, prompt):
    transport = RecordingTransport([tool_call(name="update_movie")])
    movie = MovieClient()
    service = Service(
        routed,
        transport=transport,
        movie_client=movie,
        movie_model_tools=True,
        audit=lambda _: None,
    )
    sid = service.create(LOCAL)["session_id"]
    with pytest.raises(Denied, match="tool_not_allowed"):
        await service.chat(LOCAL, sid, prompt, 0)
    assert not movie.calls and len(transport.deployments) == 1


async def test_text_path_and_concurrent_routes(routed):
    transport = RecordingTransport([])
    service = Service(routed, transport=transport, audit=lambda _: None)
    ids = [service.create(LOCAL)["session_id"] for _ in range(2)]
    await asyncio.gather(
        service.chat(LOCAL, ids[0], "Find Matrix", 0),
        service.chat(LOCAL, ids[1], "Compare movies", 0),
    )
    assert sorted(transport.deployments) == ["gpt-5", "gpt-5-mini"]


async def test_provider_rejection_never_escalates(routed):
    class Reject(RecordingTransport):
        async def complete_tool_turn(self, messages, settings):
            self.deployments.append(settings.deployment)
            raise ProviderRejected(400)

    transport = Reject([])
    service = Service(
        routed,
        transport=transport,
        movie_client=MovieClient(),
        movie_model_tools=True,
        audit=lambda _: None,
    )
    sid = service.create(LOCAL)["session_id"]
    with pytest.raises(ProviderRejected):
        await service.chat(LOCAL, sid, "Find Matrix", 0)
    assert transport.deployments == ["gpt-5-mini"]


def test_operator_override_and_single_model_compatibility(routed, settings):
    data = routed.model_dump()
    data["routing"]["mode"] = "routine"
    assert select_route(Settings.model_validate(data), "Compare movies").name == "routine"
    assert resolve_route(settings) == settings


def test_shared_mixed_route_budget_is_atomic(routed):
    from concurrent.futures import ThreadPoolExecutor

    data = routed.model_dump()
    data["limits"]["daily_usd"] = 0.023
    settings = Settings.model_validate(data)
    backend = FixtureControlBackend(
        ControlPolicy.model_validate_json(Path("config/guardrail-policy.json").read_text())
    )
    clients = [RunControls(backend, settings), RunControls(backend, settings)]
    runs = [client.start(LOCAL, str(uuid4())) for client in clients]

    def reserve(i):
        try:
            clients[i].gate(
                LOCAL,
                runs[i]["run_id"],
                runs[i]["epoch"],
                "model",
                count=1000,
                route=["routine", "reasoning"][i],
            )
            return "accepted"
        except Denied as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, [0, 1]))
    assert sorted(results) == ["accepted", "shared_daily_budget"]
    assert sum(Decimal(v) for v in backend._state["daily"].values()) <= Decimal("0.023")


async def test_route_trace_is_content_free_and_correlated(routed):
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from az_maf_agent.agent_telemetry import AgentTelemetry

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    transport = RecordingTransport([])
    service = Service(
        routed,
        transport=transport,
        audit=lambda _: None,
        agent_telemetry=AgentTelemetry(provider, "routing-test"),
    )
    sid = service.create(LOCAL)["session_id"]
    await service.chat(LOCAL, sid, "Find Matrix PRIVATE_ROUTE_CANARY", 0)
    spans = exporter.get_finished_spans()
    root = next(s for s in spans if s.attributes["gen_ai.operation.name"] == "invoke_agent")
    assert root.attributes["maf.routing.route"] == "routine"
    assert root.attributes["gen_ai.request.model"] == "gpt-5-mini"
    assert "PRIVATE_ROUTE_CANARY" not in str([dict(s.attributes) for s in spans])


async def test_routes_keep_cancellation_and_history_fence(routed):
    entered = asyncio.Event()

    class Slow(RecordingTransport):
        async def complete_tool_turn(self, messages, settings):
            entered.set()
            await asyncio.sleep(60)

    service = Service(
        routed,
        transport=Slow([]),
        movie_client=MovieClient(),
        movie_model_tools=True,
        audit=lambda _: None,
    )
    sid = service.create(LOCAL)["session_id"]
    task = asyncio.create_task(service.chat(LOCAL, sid, "Compare movies", 0))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert service.sessions[sid].revision == 0
    assert not service.sessions[sid].state.state
    assert sum(service.daily.values()) > 0


async def test_supervised_service_reserves_selected_model(routed):
    from az_maf_agent.supervisor import SafetySupervisor

    backend = FixtureControlBackend(
        ControlPolicy.model_validate_json(Path("config/guardrail-policy.json").read_text())
    )
    controls = RunControls(backend, routed)
    transport = RecordingTransport([({"role": "assistant", "content": "Matrix"}, "stop", 10)])
    service = Service(
        routed,
        transport=transport,
        movie_client=MovieClient(),
        movie_model_tools=True,
        safety=SafetySupervisor(controls),
        audit=lambda _: None,
    )
    sid = service.create(LOCAL)["session_id"]
    result = await service.chat(LOCAL, sid, "Find Matrix", 0)
    record = backend.snapshot()["runs"][result["run_id"]]
    assert record["calls"] == 1 and not record["unresolved"]
    assert Decimal(record["usd"]) == sum(service.daily.values())
    dispatch = [e for e in backend.events if e.get("capability") == "model"]
    assert dispatch[0]["model_route"] == "routine"
