import asyncio
import json

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from az_maf_agent.agent_telemetry import AgentTelemetry, operation, record_usage


def setup():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return AgentTelemetry(provider, "agent-maf-dev"), exporter


async def test_concurrent_traces_correlate_without_content():
    telemetry, exporter = setup()

    async def run():
        with telemetry.invocation():
            with operation("chat", "gpt-5", **{"gen_ai.request.model": "gpt-5"}) as model:
                await asyncio.sleep(0)
                record_usage(model, {"prompt_tokens": 12, "completion_tokens": 3})
            with operation("execute_tool", "search_movies"):
                pass

    await asyncio.gather(run(), run())
    spans = exporter.get_finished_spans()
    roots = [s for s in spans if s.attributes["gen_ai.operation.name"] == "invoke_agent"]
    assert len(roots) == 2 and roots[0].context.trace_id != roots[1].context.trace_id
    for root in roots:
        children = [s for s in spans if s.parent and s.parent.span_id == root.context.span_id]
        assert len(children) == 2
        assert all(s.context.trace_id == root.context.trace_id for s in children)
        assert root.attributes["gen_ai.usage.input_tokens"] == 12
        assert root.attributes["gen_ai.usage.output_tokens"] == 3
    assert all(not s.events for s in spans)


def test_failure_never_exports_exception_text_or_fabricates_usage():
    telemetry, exporter = setup()
    with pytest.raises(RuntimeError):
        with telemetry.invocation():
            with operation("chat", "gpt-5"):
                raise RuntimeError("SECRET-PROMPT-TOKEN-CANARY")
    spans = exporter.get_finished_spans()
    assert all(s.status.status_code == StatusCode.ERROR for s in spans)
    assert all(not s.events and s.status.description is None for s in spans)
    assert all(not any(k.startswith("gen_ai.usage.") for k in s.attributes) for s in spans)
    assert "SECRET-PROMPT-TOKEN-CANARY" not in json.dumps([dict(s.attributes) for s in spans])


async def test_actual_service_transport_correlates_model_and_mcp(configured):
    from types import SimpleNamespace

    import httpx

    from az_maf_agent.core import Principal, Service
    from az_maf_agent.model import AzureTransport

    telemetry, exporter = setup()
    settings = configured(
        mode="azure",
        endpoint="https://approved.openai.azure.com",
        deployment="gpt-5",
        api_version="2025-04-01-preview",
        input_usd_per_million=1.0,
        output_usd_per_million=1.0,
        model_context_tokens=20000,
    )
    calls = []

    class Credential:
        async def get_token(self, scope):
            return SimpleNamespace(token="SECRET-TOKEN-CANARY")

        async def close(self):
            pass

    class MCP:
        async def read(self, name, arguments):
            assert name == "get_movie" and arguments == {"catalog_id": "tmdb_11"}
            return {"synopsis": "SECRET-TOOL-RESULT-CANARY"}

        async def close(self):
            pass

    def handler(request):
        calls.append(request)
        message = (
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "get_movie", "arguments": '{"catalog_id":"tmdb_11"}'},
                    }
                ],
            }
            if len(calls) == 1
            else {"role": "assistant", "content": "SECRET-ANSWER-CANARY"}
        )
        return httpx.Response(
            200,
            json={
                "model": "gpt-5-2025-08-07",
                "choices": [
                    {
                        "message": message,
                        "finish_reason": "tool_calls" if len(calls) == 1 else "stop",
                    }
                ],
                "usage": {"total_tokens": 20, "completion_tokens": 3},
            },
        )

    transport = AzureTransport(settings, credential=Credential())
    await transport.http.aclose()
    transport.http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = Service(
        settings,
        transport=transport,
        movie_client=MCP(),
        movie_model_tools=True,
        agent_telemetry=telemetry,
        audit=lambda _: None,
    )
    principal = Principal("tenant", "user", "entra")
    sid = service.create(principal)["session_id"]
    result = await service.chat(principal, sid, "SECRET-PROMPT-CANARY", 0)
    spans = exporter.get_finished_spans()
    assert len(spans) == 4
    root = next(s for s in spans if s.parent is None)
    assert root.attributes["agent.run_id"] == result["run_id"]
    assert root.attributes["gen_ai.usage.input_tokens"] == 34
    assert root.attributes["gen_ai.usage.output_tokens"] == 6
    assert all(s.context.trace_id == root.context.trace_id for s in spans)
    assert all(s.parent is None or s.parent.span_id == root.context.span_id for s in spans)
    assert "SECRET-" not in json.dumps([dict(s.attributes) for s in spans])
    await service.close()
