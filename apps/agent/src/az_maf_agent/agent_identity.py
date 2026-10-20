"""Secretless autonomous Agent ID token exchange; never falls back to workload tokens."""

import asyncio
import time
from uuid import UUID

import httpx
from azure.core.credentials import AccessToken
from azure.identity.aio import ManagedIdentityCredential

from .model import Denied

ASSERTION = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
EXCHANGE_SCOPE = "api://AzureADTokenExchange/.default"


class AgentIdentityCredential:
    def __init__(
        self,
        tenant,
        blueprint,
        agent,
        *,
        scopes,
        managed_identity_client_id=None,
        credential=None,
        http=None,
        clock=time.time,
    ):
        self.tenant, self.blueprint, self.agent = (str(UUID(v)) for v in (tenant, blueprint, agent))
        self.scopes = frozenset(scopes)
        if (
            not self.scopes
            or len(self.scopes) > 4
            or any(not scope.endswith("/.default") for scope in self.scopes)
        ):
            raise ValueError("approved agent resource scopes required")
        self.workload = credential or ManagedIdentityCredential(
            client_id=managed_identity_client_id,
            connection_timeout=3,
            read_timeout=5,
            retry_total=0,
        )
        self.http = http or httpx.AsyncClient(timeout=8, follow_redirects=False)
        self.clock = clock
        self.cache = {}
        self.lock = asyncio.Lock()

    async def _exchange(self, values):
        try:
            response = await self.http.post(
                f"https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/token", data=values
            )
            if response.status_code != 200 or len(response.content) > 65536:
                raise Denied("agent_token_unavailable")
            payload = response.json()
            expires = payload.get("expires_in")
            token = payload.get("access_token")
            if (
                type(expires) is not int
                or not 60 < expires <= 86400
                or payload.get("token_type", "").lower() != "bearer"
                or not isinstance(token, str)
                or not 1 <= len(token) <= 32768
            ):
                raise Denied("agent_token_invalid")
            return AccessToken(token, int(self.clock()) + expires)
        except (httpx.HTTPError, ValueError, TypeError):
            raise Denied("agent_token_unavailable") from None

    async def get_token(self, *scopes, **kwargs):
        if len(scopes) != 1 or scopes[0] not in self.scopes or kwargs:
            raise Denied("agent_scope_forbidden")
        scope = scopes[0]
        async with self.lock:
            cached = self.cache.get(scope)
            if cached and cached.expires_on > self.clock() + 300:
                return cached
            # T0 authenticates only the blueprint, never the downstream resource.
            workload = await self.workload.get_token(EXCHANGE_SCOPE)
            parent = await self._exchange(
                {
                    "client_id": self.blueprint,
                    "scope": EXCHANGE_SCOPE,
                    "grant_type": "client_credentials",
                    "client_assertion": workload.token,
                    "client_assertion_type": ASSERTION,
                    "fmi_path": self.agent,
                }
            )
            token = await self._exchange(
                {
                    "client_id": self.agent,
                    "scope": scope,
                    "grant_type": "client_credentials",
                    "client_assertion_type": ASSERTION,
                    "client_assertion": parent.token,
                }
            )
            self.cache[scope] = token
            return token

    async def close(self):
        self.cache.clear()
        await self.http.aclose()
        await self.workload.close()


def configured_agent_credential(env, *, scopes):
    enabled = env.get("ENABLE_ENTRA_AGENT_ID", "false").lower()
    if enabled not in {"true", "false"}:
        raise ValueError("ENABLE_ENTRA_AGENT_ID must be true or false")
    if enabled == "false":
        return None
    return AgentIdentityCredential(
        env["ENTRA_TENANT_ID"],
        env["AGENT_BLUEPRINT_CLIENT_ID"],
        env["AGENT_IDENTITY_CLIENT_ID"],
        scopes=scopes,
        managed_identity_client_id=env.get("AGENT_FEDERATION_IDENTITY_CLIENT_ID"),
    )
