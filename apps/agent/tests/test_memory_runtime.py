import asyncio
import json
import threading

import httpx
import pytest
from test_blob_memory import BlobServer, Credential, access, make, save
from test_model_tools import MovieClient, ToolTransport

from az_maf_agent.blob_memory import BlobMemoryStore
from az_maf_agent.core import LOCAL, Service
from az_maf_agent.memory import (
    OPERATIONS,
    FixtureMemoryStore,
    MemoryAccess,
    MemoryService,
    load_memory_policy,
)
from az_maf_agent.memory_cleanup import sweep
from az_maf_agent.model import Denied


def memory_fixture():
    now = [1000.0]
    memory = MemoryService(
        load_memory_policy("config/memory-policy.json"), FixtureMemoryStore(), clock=lambda: now[0]
    )
    return memory, now


async def test_recall_is_untrusted_bounded_and_generation_clears_history(settings):
    memory, now = memory_fixture()
    transport = ToolTransport(
        [
            ({"role": "assistant", "content": "Comedy recommendation."}, "stop", 20),
            ({"role": "assistant", "content": "Fresh recommendation."}, "stop", 20),
        ]
    )
    service = Service(
        settings,
        transport=transport,
        movie_client=MovieClient(),
        movie_model_tools=True,
        memory_service=memory,
        memory_permissions=lambda _: OPERATIONS,
        audit=lambda _: None,
    )
    sid = service.create(LOCAL)["session_id"]
    owner = MemoryAccess(LOCAL.tenant, LOCAL.user, sid, "user", OPERATIONS)
    save(memory, owner)
    first = await service.chat(LOCAL, sid, "Suggest a film", 0)
    sent = transport.messages[0]
    assert "comedy" in json.dumps(sent)
    context = next(m for m in sent if "Untrusted saved" in m["content"])
    assert context["role"] == "user"
    assert "expires_at" not in context["content"] and "source_session" not in context["content"]
    assert all(
        "Untrusted saved" not in m.text
        for m in service.sessions[sid].state.state["stage1_history"]["messages"]
    )
    memory.call(owner, "forget_all")
    await service.chat(LOCAL, sid, "Suggest another", first["revision"])
    assert "comedy" not in json.dumps(transport.messages[1]).lower()
    assert "Comedy recommendation" not in json.dumps(transport.messages[1])
    assert service.sessions[sid].memory_operations == 4
    await service.close()


async def test_delete_racing_model_denies_response_and_history_commit(settings):
    memory, _ = memory_fixture()
    entered, finish = asyncio.Event(), asyncio.Event()

    class Paused(ToolTransport):
        async def complete_tool_turn(self, messages, settings):
            entered.set()
            await finish.wait()
            return {"role": "assistant", "content": "Old preference"}, "stop", 20

    service = Service(
        settings,
        transport=Paused([]),
        movie_client=MovieClient(),
        movie_model_tools=True,
        memory_service=memory,
        memory_permissions=lambda _: OPERATIONS,
        audit=lambda _: None,
    )
    sid = service.create(LOCAL)["session_id"]
    owner = MemoryAccess(LOCAL.tenant, LOCAL.user, sid, "user", OPERATIONS)
    save(memory, owner)
    task = asyncio.create_task(service.chat(LOCAL, sid, "Recommend", 0))
    await entered.wait()
    memory.call(owner, "forget_all")
    finish.set()
    with pytest.raises(Denied, match="memory_changed"):
        await task
    assert service.sessions[sid].revision == 0
    assert not service.sessions[sid].state.state.get("stage1_history", {}).get("messages")
    await service.close()


async def test_cancelled_storage_worker_keeps_slot_until_settled_and_prevents_put():
    entered, finish = threading.Event(), threading.Event()
    server = BlobServer()

    def slow(request):
        if request.method == "GET":
            entered.set()
            assert finish.wait(5)
        return server(request)

    store = BlobMemoryStore(
        "memoryfixture",
        "preferences",
        Credential(),
        httpx.Client(transport=httpx.MockTransport(slow)),
    )
    memory = MemoryService(
        load_memory_policy("config/memory-policy.json"), store, audit=lambda _: None
    )
    task = asyncio.create_task(
        memory.acall(
            access(),
            "save",
            preference={"category": "preferred_genre", "value": "comedy"},
            consent=True,
            expected_generation=0,
        )
    )
    await asyncio.to_thread(entered.wait, 5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    with pytest.raises(Denied, match="memory_busy"):
        await memory.acall(access(), "inspect")
    finish.set()
    await memory.aclose()
    assert not server.documents
    assert not memory.pending


class ListingServer(BlobServer):
    def __call__(self, request):
        if request.url.query:
            assert request.url.params["prefix"] == "movie-preferences-v1/"
            body = (
                "<EnumerationResults><Blobs>"
                + "".join(
                    "<Blob><Name>" + name.removeprefix("/preferences/") + "</Name></Blob>"
                    for name in self.documents
                )
                + "</Blobs><NextMarker /></EnumerationResults>"
            )
            return httpx.Response(200, content=body.encode())
        return super().__call__(request)


def test_cleanup_removes_expired_values_preserving_generation_and_other_users():
    server = ListingServer()
    memory = make(server)
    save(memory, access())
    memory.clock = lambda: 1000 + memory.policy.retention_seconds - 10
    save(memory, access("other"))
    result = sweep(memory.store, memory.policy, now=1000 + memory.policy.retention_seconds)
    assert result == {"examined": 2, "expired_removed": 1}
    docs = [json.loads(body) for body in server.documents.values()]
    assert sorted(d["generation"] for d in docs) == [1, 2]
    assert sorted(len(d["records"]) for d in docs) == [0, 1]
    assert memory.call(access(), "inspect")["memories"] == []
    with pytest.raises(Denied, match="memory_conflict"):
        save(memory, access())
    memory.close()


def test_cleanup_conflict_never_overwrites_concurrent_correction():
    server = ListingServer()
    memory = make(server)
    save(memory, access())
    before = dict(server.documents)
    server.conflict = True
    with pytest.raises(Denied, match="memory_conflict"):
        sweep(memory.store, memory.policy, now=1000 + memory.policy.retention_seconds)
    assert server.documents == before
    memory.close()


@pytest.mark.parametrize(
    "body",
    [
        b'<!DOCTYPE x [<!ENTITY a "bad">]><EnumerationResults/>',
        b"<EnumerationResults><Blobs><Blob><Name>../other.json</Name></Blob></Blobs></EnumerationResults>",
        b"invalid xml",
    ],
)
def test_cleanup_rejects_unapproved_names_and_xml(body):
    store = BlobMemoryStore(
        "memoryfixture",
        "preferences",
        Credential(),
        httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=body))),
    )
    with pytest.raises(Denied):
        sweep(store, load_memory_policy("config/memory-policy.json"))
    store.close()


async def test_reviewed_skill_cannot_read_memory_or_inherit_personalized_history(
    settings, tmp_path
):
    from az_maf_agent.skills import READ_TOOLS
    from test_skills import bundle

    memory, _ = memory_fixture()
    registry, _ = bundle(tmp_path)
    transport = ToolTransport(
        [
            ({"role": "assistant", "content": "Personalized comedy answer"}, "stop", 20),
            ({"role": "assistant", "content": "Catalog-only answer"}, "stop", 20),
        ]
    )
    service = Service(
        settings,
        transport=transport,
        movie_client=MovieClient(),
        movie_model_tools=True,
        memory_service=memory,
        memory_permissions=lambda _: OPERATIONS,
        skill_registry=registry,
        skill_permissions=lambda _: READ_TOOLS,
        audit=lambda _: None,
    )
    sid = service.create(LOCAL)["session_id"]
    owner = MemoryAccess(LOCAL.tenant, LOCAL.user, sid, "user", OPERATIONS)
    save(memory, owner)
    result = await service.chat(LOCAL, sid, "Suggest a film", 0)
    effects = list(memory.store.effects)
    await service.chat(
        LOCAL, sid, "Research a film", result["revision"], skill_id="test", skill_version="1.0.0"
    )
    assert memory.store.effects == effects
    assert "comedy" not in json.dumps(transport.messages[1]).lower()
    assert service.sessions[sid].memory_operations == 2
    await service.close()
