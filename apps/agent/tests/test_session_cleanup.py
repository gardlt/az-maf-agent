import json
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest

from az_maf_agent.model import Denied
from az_maf_agent.session_cleanup import sweep_sessions
from az_maf_agent.shared_sessions import SessionDocument

SID = "b166e493-ac24-4cdc-a76e-aa4e040f02ba"
OWNER = "a" * 64
NAME = "sessions/v1/" + OWNER + "/" + SID + ".json"


class Store:
    origin = "https://example/agent-sessions/movie-preferences-v1/"

    def __init__(self, *, conflict=False):
        self.marker = None
        self.deletes = []
        self.conflict = conflict
        self.pages = []
        self.document = SessionDocument(
            schema_version=1,
            session_id=SID,
            owner_ref=OWNER,
            created=0.0,
            touched=0.0,
            revision=1,
            history_epoch=1,
            movie_reads=2,
            memory_operations=1,
            active_until=0.0,
            messages=[],
        )

    def _request(self, method, url, **kwargs):
        if "maintenance" in url:
            if method == "GET":
                if self.marker is None:
                    return 404, {"x-ms-error-code": "BlobNotFound"}, b""
                return 200, {"etag": '"checkpoint"'}, json.dumps({"marker": self.marker}).encode()
            assert kwargs["conditions"] in ({"If-None-Match": "*"}, {"If-Match": '"checkpoint"'})
            self.marker = json.loads(kwargs["content"])["marker"]
            return 201, {}, b""
        if urlparse(url).query:
            marker = parse_qs(urlparse(url).query).get("marker", [""])[0]
            self.pages.append(marker)
            next_marker = "second" if marker == "" else ""
            return (
                200,
                {},
                (
                    "<EnumerationResults><Blobs><Blob><Name>"
                    + NAME
                    + "</Name></Blob></Blobs><NextMarker>"
                    + next_marker
                    + "</NextMarker></EnumerationResults>"
                ).encode(),
            )
        if method == "GET":
            return 200, {"etag": '"session"'}, self.document.model_dump_json().encode()
        assert method == "DELETE" and kwargs["conditions"] == {"If-Match": '"session"'}
        self.deletes.append(url)
        return (412 if self.conflict else 202), {}, b""


def settings():
    return SimpleNamespace(limits=SimpleNamespace(idle_seconds=1800, lifetime_seconds=14400))


def test_cleanup_cursor_continues_next_execution_and_reports_full_cycle():
    store = Store()
    first = sweep_sessions(store, settings(), now=2000.0, max_pages=1)
    assert first["sessions_removed"] == 1 and not first["session_cycle_completed"]
    assert store.marker == "second"
    second = sweep_sessions(store, settings(), now=2000.0, max_pages=1)
    assert second["session_cycle_completed"] and store.marker == ""
    assert store.pages == ["", "second"]


def test_cleanup_never_deletes_a_concurrently_changed_session():
    store = Store(conflict=True)
    result = sweep_sessions(store, settings(), now=2000.0, max_pages=1)
    assert result["sessions_examined"] == 1 and result["sessions_removed"] == 0


def test_cleanup_rejects_blob_name_document_binding_mismatch():
    store = Store()
    store.document.owner_ref = "b" * 64
    with pytest.raises(Denied, match="session_backend_invalid"):
        sweep_sessions(store, settings(), now=2000.0)
    assert store.deletes == [] and store.marker is None
