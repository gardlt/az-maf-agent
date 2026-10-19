"""Operator-only bounded expiry sweep; never exposed as an agent or HTTP tool."""

import json
import os
import re
import time
from urllib.parse import urlencode
from xml.etree import ElementTree

from .blob_memory import BlobMemoryStore, Document
from .memory import load_memory_policy
from .model import Denied


def sweep(store, policy, *, now=None, max_pages=100, deadline_seconds=480):
    now = time.time() if now is None else now
    deadline = time.monotonic() + deadline_seconds
    container = store.origin.rsplit("/movie-preferences-v1/", 1)[0]
    marker = ""
    examined = purged = 0
    for _ in range(max_pages):
        if time.monotonic() >= deadline:
            raise Denied("memory_cleanup_limit")
        query = urlencode(
            {
                "restype": "container",
                "comp": "list",
                "prefix": "movie-preferences-v1/",
                "maxresults": 50,
                "marker": marker,
            }
        )
        status, _, body = store._request("GET", container + "?" + query)
        if status != 200 or b"<!" in body:
            raise Denied("memory_cleanup_invalid")
        try:
            listing = ElementTree.fromstring(body)
        except ElementTree.ParseError:
            raise Denied("memory_cleanup_invalid") from None
        names = [node.text for node in listing.findall("./Blobs/Blob/Name")]
        if len(names) > 50:
            raise Denied("memory_cleanup_limit")
        for name in names:
            if time.monotonic() >= deadline:
                raise Denied("memory_cleanup_limit")
            if not isinstance(name, str) or not re.fullmatch(
                r"movie-preferences-v1/[0-9a-f]{64}\.json", name
            ):
                raise Denied("memory_cleanup_invalid")
            status, headers, body = store._request("GET", container + "/" + name)
            if status != 200:
                raise Denied("memory_backend_unavailable")
            try:
                doc = Document.model_validate_json(body)
                etag = headers["etag"]
                if (
                    doc.scope_ref != name.split("/")[1][:-5]
                    or not re.fullmatch(r'"[^"\r\n]{1,100}"', etag)
                    or any(
                        r.consent_policy != policy.version
                        or r.expires_at - r.updated_at > policy.retention_seconds
                        for r in doc.records
                    )
                ):
                    raise ValueError("invalid binding")
            except (KeyError, ValueError):
                raise Denied("memory_backend_invalid") from None
            examined += 1
            retained = [r for r in doc.records if r.expires_at > now]
            expired = len(doc.records) - len(retained)
            if expired:
                doc.records = retained
                doc.generation += expired
                # Log metadata only and require delivery before the conditional mutation.
                print(
                    json.dumps({"event": "memory_expiry_authorized", "count": expired}), flush=True
                )
                status, _, _ = store._request(
                    "PUT",
                    container + "/" + name,
                    content=doc.model_dump_json().encode(),
                    conditions={"If-Match": etag},
                )
                if status in (409, 412):
                    raise Denied("memory_conflict")
                if status != 201:
                    raise Denied("memory_backend_unavailable")
                purged += expired
        next_marker = listing.findtext("NextMarker") or ""
        if not next_marker:
            return {"examined": examined, "expired_removed": purged}
        if next_marker == marker or len(next_marker) > 2048:
            raise Denied("memory_cleanup_invalid")
        marker = next_marker
    raise Denied("memory_cleanup_limit")


def main():
    store = BlobMemoryStore(os.environ["MEMORY_ACCOUNT"], os.environ["MEMORY_CONTAINER"])
    try:
        result = sweep(store, load_memory_policy(os.environ["MEMORY_POLICY"]))
        if os.environ.get("SESSION_ACCOUNT"):
            from .config import load_settings
            from .session_cleanup import sweep_sessions

            session_store = BlobMemoryStore(os.environ["SESSION_ACCOUNT"], "agent-sessions")
            try:
                result.update(
                    sweep_sessions(session_store, load_settings(os.environ["SESSION_CONFIG"]))
                )
            finally:
                session_store.close()
        print(json.dumps({"event": "memory_cleanup_completed", **result}), flush=True)
    except Exception:
        print(json.dumps({"event": "memory_cleanup_failed"}), flush=True)
        raise SystemExit(1) from None
    finally:
        store.close()


if __name__ == "__main__":
    main()
