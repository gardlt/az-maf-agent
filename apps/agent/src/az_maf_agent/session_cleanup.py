"""Bounded short-term-session cleanup with a durable continuation cursor."""

import json
import re
import time
from urllib.parse import urlencode
from xml.etree import ElementTree

from .guardrail_blob import UUID_PATTERN
from .model import Denied
from .shared_sessions import MAX_SESSION_BYTES, SessionDocument


def sweep_sessions(store, settings, *, now=None, max_pages=40, deadline_seconds=480):
    now = time.time() if now is None else now
    deadline = time.monotonic() + deadline_seconds
    base = store.origin.rsplit("/movie-preferences-v1/", 1)[0] + "/"
    checkpoint = base + "maintenance/session-cleanup.json"
    status, headers, body = store._request("GET", checkpoint)
    if status == 404 and headers.get("x-ms-error-code") == "BlobNotFound":
        marker = ""
        condition = {"If-None-Match": "*"}
    elif status == 200:
        try:
            saved = json.loads(body)
            marker = saved["marker"]
            etag = headers["etag"]
            if (
                set(saved) != {"marker"}
                or not isinstance(marker, str)
                or len(marker) > 2048
                or not re.fullmatch(r'"[^"\r\n]{1,100}"', etag)
            ):
                raise ValueError("invalid checkpoint")
        except (KeyError, ValueError):
            raise Denied("session_cleanup_invalid") from None
        condition = {"If-Match": etag}
    else:
        raise Denied("session_backend_unavailable")
    examined = deleted = 0
    full_cycle = False
    for _ in range(max_pages):
        if time.monotonic() >= deadline:
            break
        query = urlencode(
            {
                "restype": "container",
                "comp": "list",
                "prefix": "sessions/v1/",
                "maxresults": 25,
                "marker": marker,
            }
        )
        status, _, body = store._request("GET", base + "?" + query, max_bytes=131072)
        if status != 200 or b"<!" in body:
            raise Denied("session_cleanup_invalid")
        try:
            page = ElementTree.fromstring(body)
        except ElementTree.ParseError:
            raise Denied("session_cleanup_invalid") from None
        names = [node.text for node in page.findall("./Blobs/Blob/Name")]
        if len(names) > 25:
            raise Denied("session_cleanup_invalid")
        finished_page = True
        for name in names:
            if time.monotonic() >= deadline:
                finished_page = False
                break
            if not isinstance(name, str) or not re.fullmatch(
                r"sessions/v1/[0-9a-f]{64}/" + UUID_PATTERN.strip("^$") + r"\.json", name
            ):
                raise Denied("session_cleanup_invalid")
            status, headers, body = store._request("GET", base + name, max_bytes=MAX_SESSION_BYTES)
            if status == 404 and headers.get("x-ms-error-code") == "BlobNotFound":
                continue
            if status != 200:
                raise Denied("session_backend_unavailable")
            try:
                document = SessionDocument.model_validate_json(body)
                etag = headers["etag"]
                if (
                    name
                    != "sessions/v1/" + document.owner_ref + "/" + document.session_id + ".json"
                    or not re.fullmatch(r'"[^"\r\n]{1,100}"', etag)
                ):
                    raise ValueError("invalid session binding")
            except (ValueError, KeyError):
                raise Denied("session_backend_invalid") from None
            examined += 1
            if (
                now - document.touched >= settings.limits.idle_seconds
                or now - document.created >= settings.limits.lifetime_seconds
            ):
                print(json.dumps({"event": "session_expiry_authorized", "count": 1}), flush=True)
                status, _, _ = store._request("DELETE", base + name, conditions={"If-Match": etag})
                if status == 202:
                    deleted += 1
                elif status not in (404, 409, 412):
                    raise Denied("session_backend_unavailable")
        if not finished_page:
            break  # Revisit this page next execution; never skip unprocessed rows.
        next_marker = page.findtext("NextMarker") or ""
        if not next_marker:
            marker = ""
            full_cycle = True
            break
        if next_marker == marker or len(next_marker) > 2048:
            raise Denied("session_cleanup_invalid")
        marker = next_marker
    status, _, _ = store._request(
        "PUT", checkpoint, content=json.dumps({"marker": marker}).encode(), conditions=condition
    )
    if status != 201:
        raise Denied("session_cleanup_conflict")
    return {
        "sessions_examined": examined,
        "sessions_removed": deleted,
        "session_cycle_completed": full_cycle,
    }
