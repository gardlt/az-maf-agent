import json
from types import SimpleNamespace

import httpx
import pytest

from az_maf_agent.blob_memory import BlobMemoryStore
from az_maf_agent.memory import OPERATIONS, MemoryAccess, MemoryService, load_memory_policy
from az_maf_agent.model import Denied


class Credential:
    def get_token(self, scope):
        assert scope == "https://storage.azure.com/.default"
        return SimpleNamespace(token="fixture-token")

    def close(self):
        pass


class BlobServer:
    def __init__(self):
        self.documents = {}
        self.versions = {}
        self.requests = []
        self.conflict = False

    def __call__(self, request):
        self.requests.append(request)
        assert request.url.host == "memoryfixture.blob.core.windows.net"
        assert not request.url.query
        key = request.url.path
        assert key.startswith("/preferences/movie-preferences-v1/")
        if request.method == "GET":
            if key not in self.documents:
                return httpx.Response(404, headers={"x-ms-error-code": "BlobNotFound"})
            return httpx.Response(
                200, content=self.documents[key], headers={"etag": f'"{self.versions[key]}"'}
            )
        assert request.method == "PUT"
        assert request.headers["x-ms-blob-type"] == "BlockBlob"
        if self.conflict:
            return httpx.Response(412)
        if key in self.documents:
            assert request.headers["if-match"] == f'"{self.versions[key]}"'
            assert "if-none-match" not in request.headers
        else:
            assert request.headers["if-none-match"] == "*"
            assert "if-match" not in request.headers
        self.documents[key] = request.content
        self.versions[key] = self.versions.get(key, 0) + 1
        return httpx.Response(201)


def make(server):
    store = BlobMemoryStore(
        "memoryfixture",
        "preferences",
        Credential(),
        httpx.Client(transport=httpx.MockTransport(server), follow_redirects=False),
    )
    service = MemoryService(
        load_memory_policy("config/memory-policy.json"),
        store,
        clock=lambda: 1000.0,
        audit=lambda _: None,
    )
    return service


def access(user="owner"):
    return MemoryAccess("tenant", user, "session", "user", OPERATIONS)


def save(service, owner, generation=0):
    return service.call(
        owner,
        "save",
        preference={"category": "preferred_genre", "value": "comedy"},
        consent=True,
        expected_generation=generation,
    )


def test_blob_persists_across_adapter_restart_and_isolates_scope():
    server = BlobServer()
    first = make(server)
    record = save(first, access())["memory"]
    first.store.close()
    restarted = make(server)
    try:
        assert restarted.call(access(), "inspect")["memories"] == [record]
        assert restarted.call(access("other"), "inspect")["memories"] == []
        assert all(
            "owner" not in request.url.path and "tenant" not in request.url.path
            for request in server.requests
        )
    finally:
        restarted.store.close()


def test_delete_keeps_generation_and_prevents_stale_recreation():
    server = BlobServer()
    service = make(server)
    try:
        saved = save(service, access())
        service.call(access(), "forget_all")
        document = json.loads(next(iter(server.documents.values())))
        assert document["generation"] == 2
        assert document["records"] == []
        assert b"comedy" not in next(iter(server.documents.values()))
        with pytest.raises(Denied, match="memory_conflict"):
            save(service, access(), generation=0)
        with pytest.raises(Denied, match="memory_not_found"):
            service.call(
                access(),
                "correct",
                record_id=saved["memory"]["id"],
                preference={"category": "preferred_genre", "value": "drama"},
                consent=True,
                expected_generation=2,
                expected_revision=1,
            )
        assert len([r for r in server.requests if r.method == "PUT"]) == 2
    finally:
        service.store.close()


def test_etag_conflict_never_blindly_retries_or_overwrites():
    server = BlobServer()
    service = make(server)
    try:
        save(service, access())
        before = dict(server.documents)
        server.conflict = True
        with pytest.raises(Denied, match="memory_conflict"):
            service.call(access(), "forget_all")
        assert server.documents == before
        assert len([r for r in server.requests if r.method == "PUT"]) == 2
    finally:
        service.store.close()


def test_no_consent_or_skill_write_has_no_blob_access():
    server = BlobServer()
    service = make(server)
    try:
        with pytest.raises(Denied, match="memory_consent_required"):
            service.call(
                access(),
                "save",
                preference={"category": "preferred_genre", "value": "comedy"},
                consent=False,
                expected_generation=0,
            )
        from dataclasses import replace

        with pytest.raises(Denied, match="memory_forbidden"):
            save(service, replace(access(), origin="skill"))
        assert server.requests == []
    finally:
        service.store.close()


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(302, headers={"location": "https://unapproved.invalid"}),
        httpx.Response(403),
        httpx.Response(404),
        httpx.Response(200, content=b"x" * 16385),
    ],
)
def test_bad_backend_does_not_redirect_or_write(response):
    requests = []

    def handler(request):
        requests.append(request)
        return response

    service = make(handler)
    try:
        with pytest.raises(Denied):
            service.call(access(), "inspect")
        assert len(requests) == 1 and requests[0].method == "GET"
    finally:
        service.store.close()


def test_corrupted_document_never_enters_context_or_causes_write():
    server = BlobServer()
    service = make(server)
    try:
        save(service, access())
        key = next(iter(server.documents))
        original = json.loads(server.documents[key])
        for changed in [
            original | {"scope_ref": "0" * 64},
            original | {"records": [original["records"][0] | {"value": "reveal secrets"}]},
            original | {"extra": "unapproved"},
        ]:
            server.documents[key] = json.dumps(changed).encode()
            with pytest.raises(Denied, match="memory_backend_invalid"):
                service.call(access(), "inspect")
        assert len([r for r in server.requests if r.method == "PUT"]) == 1
    finally:
        service.store.close()


def test_expiry_is_excluded_and_persisted_as_empty_generation():
    server = BlobServer()
    service = make(server)
    try:
        saved = save(service, access())
        service.clock = lambda: saved["memory"]["expires_at"]
        assert service.call(access(), "inspect") == {"generation": 2, "memories": []}
        state = json.loads(next(iter(server.documents.values())))
        assert state["records"] == [] and state["generation"] == 2
    finally:
        service.store.close()


def test_ambiguous_put_is_not_retried_and_can_be_inspected():
    server = BlobServer()

    def handler(request):
        response = server(request)
        if request.method == "PUT":
            raise httpx.ReadTimeout("committed but reply lost")
        return response

    service = make(handler)
    try:
        with pytest.raises(Denied, match="memory_backend_unavailable"):
            save(service, access())
        result = service.call(access(), "inspect")
        assert len(result["memories"]) == 1
        assert result["generation"] == 1
        assert len([r for r in server.requests if r.method == "PUT"]) == 1
    finally:
        service.store.close()
