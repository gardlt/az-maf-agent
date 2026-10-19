import time
from types import SimpleNamespace
from uuid import uuid4

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from az_maf_agent.api import EntraVerifier, create_app
from az_maf_agent.core import Service


class FakeMovieClient:
    async def read(self, name, arguments):
        if name != "get_movie":
            raise AssertionError("unexpected tool")
        return {
            "catalog_version": "tmdb-v1",
            "movie": {
                "id": arguments["catalog_id"],
                "title": "Star Wars",
                "year": 1977,
                "synopsis": "A movie.",
                "tmdb_rating": 8.2,
                "source": "TMDB",
            },
        }

    async def close(self):
        pass


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
                json={"catalog_id": "tmdb_11"},
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
    app.state.agent_service.movie_client = FakeMovieClient()
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="https://test"
        ) as c:
            sid = (await c.post("/sessions", headers=auth())).json()["session_id"]
            path = f"/sessions/{sid}/movies/get_movie"
            assert (await c.post(path, json={"catalog_id": "tmdb_11"})).status_code == 401
            assert (
                await c.post(path, headers=auth(oid=other), json={"catalog_id": "tmdb_11"})
            ).status_code == 404
            good = await c.post(path, headers=auth(), json={"catalog_id": "tmdb_11"})
            assert good.status_code == 200
            assert good.json()["movie"]["title"] == "Star Wars"
            forbidden = await c.post(
                f"/sessions/{sid}/movies/put_movie",
                headers=auth(),
                json={"catalog_id": "tmdb_11"},
            )
            assert forbidden.status_code == 403
    finally:
        await app.state.agent_service.close()


async def test_about_credits_require_authentication(api):
    app, auth, _ = api
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="https://test") as c:
        assert (await c.get("/about")).status_code == 401
        page = await c.get("/about", headers=auth())
        assert page.status_code == 200
        assert "text/html" in page.headers["content-type"]
        assert (
            "This product uses the TMDB API but is not endorsed or certified by TMDB." in page.text
        )
        assert (
            "blue_square_2-d537fb228cf3ded904ef09b136fe3fec72548ebc1fea3fbbd1ad9e36364db38b.svg"
            in page.text
        )


async def test_memory_apis_disabled_by_default(api):
    app, auth, _ = api
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="https://test"
    ) as client:
        sid = (await client.post("/sessions", headers=auth())).json()["session_id"]
        response = await client.get(f"/sessions/{sid}/memory", headers=auth())
        assert response.status_code == 403
        assert response.json() == {"error": "memory_not_enabled"}


async def test_authenticated_memory_lifecycle_uses_owned_scope(api):
    from az_maf_agent.memory import OPERATIONS, FixtureMemoryStore, MemoryPolicy, MemoryService

    app, auth, other = api
    service = app.state.agent_service
    store = FixtureMemoryStore()
    service.memory_service = MemoryService(
        MemoryPolicy("stage-4-movie-preferences-v1", "user", 30 * 86400, 2, 8), store
    )
    service.memory_permissions = lambda _: OPERATIONS
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="https://test"
    ) as client:
        sid = (await client.post("/sessions", headers=auth())).json()["session_id"]
        path = f"/sessions/{sid}/memory"
        body = {
            "category": "preferred_genre",
            "value": "comedy",
            "consent": True,
            "expected_generation": 0,
        }
        assert (await client.post(path, json=body)).status_code == 401
        assert (
            await client.post(path, headers=auth(), json=body | {"user": other})
        ).status_code == 422
        assert not store.effects
        response = await client.post(path, headers=auth(), json=body)
        assert response.status_code == 200
        record = response.json()["memory"]
        assert (await client.get(path, headers=auth(oid=other))).status_code == 404
        stranger = (await client.post("/sessions", headers=auth(oid=other))).json()["session_id"]
        stranger_path = f"/sessions/{stranger}/memory"
        assert (await client.get(stranger_path, headers=auth(oid=other))).json()["memories"] == []
        denied = await client.put(
            stranger_path + "/" + record["id"],
            headers=auth(oid=other),
            json=body | {"value": "drama", "expected_revision": 1},
        )
        assert denied.status_code == 404
        next_sid = (await client.post("/sessions", headers=auth())).json()["session_id"]
        next_path = f"/sessions/{next_sid}/memory"
        assert (await client.get(next_path, headers=auth())).json()["memories"] == [record]
        before = list(store.effects)
        refused = await client.post(next_path, headers=auth(), json=body | {"consent": False})
        assert refused.status_code == 403
        assert store.effects == before
        corrected = await client.put(
            next_path + "/" + record["id"],
            headers=auth(),
            json=body | {"value": "drama", "expected_generation": 1, "expected_revision": 1},
        )
        assert corrected.status_code == 200
        assert corrected.json()["memory"]["revision"] == 2
        assert (await client.delete(next_path, headers=auth())).status_code == 200
        stale = await client.post(next_path, headers=auth(), json=body | {"expected_generation": 2})
        assert stale.status_code == 409
        assert (await client.get(next_path, headers=auth())).json()["memories"] == []
