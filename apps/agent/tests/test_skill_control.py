import json
from types import SimpleNamespace

import httpx
import pytest

from az_maf_agent.model import Denied
from az_maf_agent.skill_control import AzureTagControl

RESOURCE = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/dev/providers/Microsoft.App/containerApps/agent"


class Credential:
    def get_token(self, scope):
        assert scope == "https://management.azure.com/.default"
        return SimpleNamespace(token="fixture-not-a-secret")

    def close(self):
        pass


def test_control_reads_each_gate_and_rejects_redirect():
    calls = []

    def handler(request):
        calls.append(request)
        assert request.url.host == "management.azure.com"
        if len(calls) == 3:
            return httpx.Response(302, headers={"location": "https://unapproved.invalid"})
        state = {"generation": len(calls), "disabled": [], "revoked": []}
        return httpx.Response(
            200, json={"properties": {"tags": {"maf-skill-control": json.dumps(state)}}}
        )

    reader = AzureTagControl(
        RESOURCE, Credential(), httpx.Client(transport=httpx.MockTransport(handler))
    )
    assert reader()["generation"] == 1
    assert reader()["generation"] == 2
    with pytest.raises(Denied, match="skill_control_unavailable"):
        reader()
    assert len(calls) == 3
    reader.close()


@pytest.mark.parametrize(
    "response",
    [httpx.Response(403), httpx.Response(200, json={}), httpx.Response(200, content=b"x" * 16385)],
)
def test_control_failure_is_closed(response):
    reader = AzureTagControl(
        RESOURCE, Credential(), httpx.Client(transport=httpx.MockTransport(lambda _: response))
    )
    with pytest.raises(Denied, match="skill_control_unavailable"):
        reader()
    reader.close()


def test_transient_network_retry_uses_fresh_control_state():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ReadTimeout("fixture timeout")
        state = {"generation": 7, "disabled": ["movie-night@1.0.0"], "revoked": []}
        return httpx.Response(
            200, json={"properties": {"tags": {"maf-skill-control": json.dumps(state)}}}
        )

    reader = AzureTagControl(
        RESOURCE, Credential(), httpx.Client(transport=httpx.MockTransport(handler))
    )
    assert reader()["disabled"] == ["movie-night@1.0.0"]
    assert len(calls) == 2
    reader.close()
