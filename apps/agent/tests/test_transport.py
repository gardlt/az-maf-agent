import json
from types import SimpleNamespace

import httpx
import pytest
from agent_framework import Message

from az_maf_agent.model import AzureTransport, Denied, Transient


class Credential:
    async def get_token(self, scope):
        assert scope == "https://cognitiveservices.azure.com/.default"
        return SimpleNamespace(token="synthetic-token")

    async def close(self):
        pass


def live(configured):
    return configured(
        mode="azure",
        endpoint="https://approved.openai.azure.com",
        deployment="configured-deployment",
        api_version="approved-version",
        input_usd_per_million=1.0,
        output_usd_per_million=1.0,
        model_context_tokens=20000,
    )


async def transport(configured, handler):
    cfg = live(configured)
    t = AzureTransport(cfg)
    await t.credential.close()
    await t.http.aclose()
    t.credential = Credential()
    t.http = httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)
    return cfg, t


async def test_live_request_no_tools_or_unconfigured_destination(configured):
    def handler(request):
        assert request.url.host == "approved.openai.azure.com"
        assert "/configured-deployment/" in request.url.path
        payload = json.loads(request.content)
        assert "tools" not in payload and payload["store"] is False
        assert payload["max_completion_tokens"] == 2000
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "ok"}}],
                "usage": {"total_tokens": 100, "completion_tokens": 2},
            },
        )

    cfg, t = await transport(configured, handler)
    assert await t.complete([Message("user", ["hello"])], cfg) == ("ok", 100)
    await t.close()


async def test_live_tool_request_advertises_only_pinned_reads(configured):
    def handler(request):
        payload = json.loads(request.content)
        assert payload["parallel_tool_calls"] is False
        assert payload["store"] is False
        assert {tool["function"]["name"] for tool in payload["tools"]} == {
            "search_movies",
            "get_movie",
        }
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "A synthetic movie."},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"total_tokens": 100, "completion_tokens": 10},
            },
        )

    cfg, t = await transport(configured, handler)
    assert await t.complete_tool_turn([{"role": "user", "content": "movie"}], cfg) == (
        {"role": "assistant", "content": "A synthetic movie."},
        "stop",
        100,
    )
    await t.close()


@pytest.mark.parametrize(
    "kind,code",
    [
        ("tool", "tools_disabled"),
        ("bad", "provider_shape"),
        ("large", "provider_size"),
        ("redirect", "provider_failure"),
    ],
)
async def test_hostile_responses(configured, kind, code):
    calls = []

    def handler(request):
        calls.append(request.url)
        if kind == "tool":
            return httpx.Response(
                200, json={"choices": [{"message": {"tool_calls": [{"name": "shell"}]}}]}
            )
        if kind == "bad":
            return httpx.Response(200, content=b"not json")
        if kind == "large":
            return httpx.Response(200, content=b"x" * 65537)
        return httpx.Response(302, headers={"location": "https://unapproved.invalid"})

    cfg, t = await transport(configured, handler)
    with pytest.raises(Denied, match=code):
        await t.complete([Message("user", ["x"])], cfg)
    assert len(calls) == 1
    await t.close()


async def test_transient_without_payload_disclosure(configured):
    cfg, t = await transport(configured, lambda r: httpx.Response(429, text="synthetic-secret"))
    with pytest.raises(Transient) as exc:
        await t.complete([Message("user", ["x"])], cfg)
    assert "synthetic-secret" not in str(exc.value)
    await t.close()


@pytest.mark.parametrize("tool_mode", [False, True])
async def test_configured_reasoning_effort_keeps_existing_output_bound(configured, tool_mode):
    def handler(request):
        payload = json.loads(request.content)
        assert payload["reasoning_effort"] == "minimal"
        assert payload["max_completion_tokens"] == 2000
        assert payload["store"] is False
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}
                ],
                "usage": {"total_tokens": 19, "completion_tokens": 2},
            },
        )

    cfg, t = await transport(configured, handler)
    cfg = cfg.model_copy(update={"reasoning_effort": "minimal"})
    if tool_mode:
        await t.complete_tool_turn([{"role": "user", "content": "movie"}], cfg)
    else:
        await t.complete([Message("user", ["hello"])], cfg)
    await t.close()


@pytest.mark.parametrize("status", [400, 401, 403, 404, 405, 413, 415, 422])
async def test_confirmed_http_rejection_is_typed_without_response_content(configured, status):
    from az_maf_agent.model import ProviderRejected

    cfg, t = await transport(
        configured,
        lambda request: httpx.Response(
            status, json={"error": {"message": "SENSITIVE_ERROR_CANARY"}}
        ),
    )
    with pytest.raises(ProviderRejected) as caught:
        await t.complete([Message("user", ["hello"])], cfg)
    assert caught.value.status == status
    assert "SENSITIVE_ERROR_CANARY" not in str(caught.value)
    await t.close()


async def test_rejection_diagnostic_emits_only_allowlisted_category(configured, capsys):
    from az_maf_agent.model import ProviderRejected

    cfg, t = await transport(
        configured,
        lambda request: httpx.Response(
            400,
            json={
                "error": {
                    "code": "content_filter",
                    "message": "SENSITIVE_ERROR_CANARY",
                    "innererror": {"code": "ResponsibleAIPolicyViolation"},
                }
            },
        ),
    )
    with pytest.raises(ProviderRejected) as caught:
        await t.complete([Message("user", ["hello"])], cfg)
    assert caught.value.category == "content_policy"
    output = capsys.readouterr().out
    assert "content_policy" in output and "SENSITIVE_ERROR_CANARY" not in output
    await t.close()
