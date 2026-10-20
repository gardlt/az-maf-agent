import asyncio
from types import SimpleNamespace

import httpx
import pytest

from az_maf_agent.agent_identity import AgentIdentityCredential, configured_agent_credential
from az_maf_agent.model import Denied

TENANT = "11111111-1111-4111-8111-111111111111"
BLUEPRINT = "22222222-2222-4222-8222-222222222222"
AGENT = "33333333-3333-4333-8333-333333333333"
SCOPE = "https://cognitiveservices.azure.com/.default"


class Workload:
    async def get_token(self, scope):
        assert scope == "api://AzureADTokenExchange/.default"
        return SimpleNamespace(token="workload-secret")

    async def close(self):
        pass


async def test_federated_exchange_cache_refresh_and_scope_fence():
    from urllib.parse import parse_qs

    requests = []
    clock = [1000]

    def handler(request):
        body = parse_qs(request.content.decode())
        requests.append(body)
        assert request.url.host == "login.microsoftonline.com"
        if body["client_id"] == [BLUEPRINT]:
            assert body["fmi_path"] == [AGENT]
            assert body["client_assertion"] == ["workload-secret"]
            token = "parent-secret"
        else:
            assert body["client_id"] == [AGENT]
            assert body["scope"] == [SCOPE]
            assert body["client_assertion"] == ["parent-secret"]
            token = "agent-secret"
        return httpx.Response(
            200, json={"access_token": token, "expires_in": 3600, "token_type": "Bearer"}
        )

    credential = AgentIdentityCredential(
        TENANT,
        BLUEPRINT,
        AGENT,
        scopes={SCOPE},
        credential=Workload(),
        http=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        clock=lambda: clock[0],
    )
    tokens = await asyncio.gather(*(credential.get_token(SCOPE) for _ in range(10)))
    assert all(token.token == "agent-secret" for token in tokens)
    assert len(requests) == 2  # Concurrent callers reuse the cached agent token.
    clock[0] += 3400
    await credential.get_token(SCOPE)
    assert len(requests) == 4
    with pytest.raises(Denied, match="agent_scope_forbidden"):
        await credential.get_token("https://graph.microsoft.com/.default")
    assert len(requests) == 4
    await credential.close()


@pytest.mark.parametrize(
    "status,payload", [(302, {}), (403, {}), (200, {"access_token": "secret"})]
)
async def test_no_workload_fallback_or_redirect(status, payload):
    credential = AgentIdentityCredential(
        TENANT,
        BLUEPRINT,
        AGENT,
        scopes={SCOPE},
        credential=Workload(),
        http=httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    status, json=payload, headers={"location": "https://unapproved.invalid"}
                )
            )
        ),
    )
    with pytest.raises(Denied, match="agent_token_"):
        await credential.get_token(SCOPE)
    assert not credential.cache
    await credential.close()


def test_enabled_identity_never_silently_falls_back():
    assert configured_agent_credential({}, scopes={SCOPE}) is None
    with pytest.raises(KeyError):
        configured_agent_credential({"ENABLE_ENTRA_AGENT_ID": "true"}, scopes={SCOPE})
