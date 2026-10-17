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
