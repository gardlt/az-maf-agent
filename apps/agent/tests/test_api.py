import time
from types import SimpleNamespace
from uuid import uuid4

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from az_maf_agent.api import EntraVerifier, create_app
from az_maf_agent.core import Service
from az_maf_agent.movie_mcp import MovieMCPClient


@pytest.fixture
def api(settings):
    tenant, user, other = str(uuid4()), str(uuid4()), str(uuid4())
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class Keys:
        def get_signing_key_from_jwt(self, token):
            return SimpleNamespace(key=private.public_key())

    verifier = EntraVerifier(tenant, "api-test", {user, other}, Keys())
    service = Service(settings, audit=lambda e: None)
    app = create_app(service, verifier)
    app.state.agent_service = service

    def headers(**changes):
        now = int(time.time())
        claims = dict(
            iss=verifier.issuer,
            aud="api-test",
            exp=now + 60,
            iat=now,
            nbf=now - 1,
            tid=tenant,
            oid=user,
            sub=user,
            scp="Chat.Access",
        )
        claims.update(changes)
        return {"Authorization": "Bearer " + jwt.encode(claims, private, algorithm="RS256")}

    return app, headers, other


async def test_auth_and_body_identity(api):
    app, auth, other = api
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="https://test") as c:
        assert (
            await c.post("/sessions", headers={"x-ms-client-principal": "forged-admin"})
        ).status_code == 401
        for changes in [dict(exp=1), dict(aud="wrong"), dict(iss="wrong"), dict(tid=str(uuid4()))]:
            assert (await c.post("/sessions", headers=auth(**changes))).status_code == 401
        assert (await c.post("/sessions", headers=auth(scp=""))).status_code == 403
        assert (await c.post("/sessions", headers=auth(oid=str(uuid4())))).status_code == 403
        sid = (await c.post("/sessions", headers=auth())).json()["session_id"]
        assert (
            await c.post(
                f"/sessions/{sid}/movies/get_movie",
                headers=auth(),
                json={"catalog_id": "movie_000101"},
            )
        ).status_code == 403
        path = f"/sessions/{sid}/chat"
        assert (
            await c.post(
                path, headers=auth(), json={"text": "hello", "revision": 0, "user": "admin"}
            )
        ).status_code == 422
        assert (
            await c.post(path, headers=auth(oid=other), json={"text": "hello", "revision": 0})
        ).status_code == 404
        assert (
            await c.post(path, headers=auth(), json={"text": "hello", "revision": 0})
        ).status_code == 200
        assert (
            await c.post(path, headers=auth(), json={"text": "replay", "revision": 0})
        ).status_code == 409
        assert (await c.post(path, headers=auth(), content=b"x" * 32769)).status_code == 413
        assert (await c.get("/docs")).status_code == 404


async def test_authenticated_movie_route_keeps_read_only_scope(api):
    app, auth, other = api
    app.state.agent_service.movie_client = MovieMCPClient()
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="https://test"
        ) as c:
            sid = (await c.post("/sessions", headers=auth())).json()["session_id"]
            path = f"/sessions/{sid}/movies/get_movie"
            assert (await c.post(path, json={"catalog_id": "movie_000101"})).status_code == 401
            assert (
                await c.post(path, headers=auth(oid=other), json={"catalog_id": "movie_000101"})
            ).status_code == 404
            good = await c.post(path, headers=auth(), json={"catalog_id": "movie_000101"})
            assert good.status_code == 200
            assert good.json()["movie"]["title"] == "Brass Comet"
            forbidden = await c.post(
                f"/sessions/{sid}/movies/put_movie",
                headers=auth(),
                json={"catalog_id": "movie_000101"},
            )
            assert forbidden.status_code == 403
    finally:
        await app.state.agent_service.close()
