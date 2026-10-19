"""Scoped short-term Blob sessions with CAS fencing, never preference memory."""

import copy
import re
import threading
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .blob_memory import BlobMemoryStore
from .guardrail_blob import UUID_PATTERN
from .guardrails import scope_ref
from .model import Denied

MAX_SESSION_BYTES = 65536


class HistoryMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    role: Literal["user", "assistant"]
    text: str = Field(max_length=32768)


class SessionDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: int = Field(ge=1, le=1)
    session_id: str = Field(pattern=UUID_PATTERN)
    owner_ref: str = Field(pattern=r"^[0-9a-f]{64}$")
    created: float = Field(ge=0, allow_inf_nan=False)
    touched: float = Field(ge=0, allow_inf_nan=False)
    revision: int = Field(ge=0)
    history_epoch: int = Field(ge=0)
    movie_reads: int = Field(ge=0)
    memory_operations: int = Field(ge=0)
    active_run: str | None = Field(default=None, pattern=UUID_PATTERN)
    active_until: float = Field(ge=0, allow_inf_nan=False)
    memory_generation: int | None = Field(default=None, ge=0)
    messages: list[HistoryMessage] = Field(max_length=1000)

    @model_validator(mode="after")
    def valid_history(self):
        if self.created > self.touched or sum(len(m.text.encode()) for m in self.messages) > 32768:
            raise ValueError("invalid session history")
        if len(self.messages) % 2 or any(
            m.role != ("user" if index % 2 == 0 else "assistant")
            for index, m in enumerate(self.messages)
        ):
            raise ValueError("invalid turn sequence")
        return self


class FixtureSessionBackend:
    def __init__(self):
        self.documents = {}
        self.lock = threading.RLock()

    def read(self, key):
        with self.lock:
            if key not in self.documents:
                raise Denied("session_not_found")
            return copy.deepcopy(self.documents[key])

    def create(self, key, document):
        with self.lock:
            if key in self.documents:
                raise Denied("session_conflict")
            self.documents[key] = copy.deepcopy(document)

    def transact(self, key, transition):
        with self.lock:
            document = self.read(key)
            result = transition(document)
            self.documents[key] = copy.deepcopy(document)
            return result

    def close(self):
        pass


class BlobSessionBackend:
    def __init__(self, account, credential=None):
        self.store = BlobMemoryStore(account, "agent-sessions", credential=credential)
        self.origin = self.store.origin.rsplit("/movie-preferences-v1/", 1)[0] + "/sessions/v1/"

    def _read(self, key):
        status, headers, body = self.store._request(
            "GET", self.origin + key + ".json", max_bytes=MAX_SESSION_BYTES
        )
        if status == 404 and headers.get("x-ms-error-code") == "BlobNotFound":
            raise Denied("session_not_found")
        if status != 200:
            raise Denied("session_backend_unavailable")
        try:
            document = SessionDocument.model_validate_json(body).model_dump()
            if key != document["owner_ref"] + "/" + document["session_id"]:
                raise ValueError("invalid binding")
            etag = headers["etag"]
            if not re.fullmatch(r'"[^"\r\n]{1,100}"', etag):
                raise ValueError("invalid etag")
        except (ValueError, KeyError):
            raise Denied("session_backend_invalid") from None
        return document, etag

    def read(self, key):
        return self._read(key)[0]

    def _put(self, key, document, conditions):
        try:
            payload = SessionDocument.model_validate(document).model_dump_json().encode()
        except ValueError:
            raise Denied("session_backend_invalid") from None
        if len(payload) > MAX_SESSION_BYTES:
            raise Denied("session_backend_invalid")
        status, _, _ = self.store._request(
            "PUT", self.origin + key + ".json", content=payload, conditions=conditions
        )
        if status in (409, 412):
            raise Denied("session_conflict")
        if status != 201:
            raise Denied("session_backend_unavailable")

    def create(self, key, document):
        self._put(key, document, {"If-None-Match": "*"})

    def transact(self, key, transition):
        # Only a confirmed failed CAS may retry; never retry an ambiguous PUT.
        for attempt in range(3):
            document, etag = self._read(key)
            result = transition(document)
            try:
                self._put(key, document, {"If-Match": etag})
                return result
            except Denied as exc:
                if exc.code != "session_conflict" or attempt == 2:
                    raise

    def close(self):
        self.store.close()


class SessionRepository:
    def __init__(self, backend, settings, clock=time.time):
        self.backend, self.settings, self.clock = backend, settings, clock

    def key(self, principal, sid):
        if not isinstance(sid, str) or not re.fullmatch(UUID_PATTERN, sid):
            raise Denied("session_not_found")
        return scope_ref(principal) + "/" + sid

    def _live(self, document):
        now = self.clock()
        if (
            now - document["touched"] >= self.settings.limits.idle_seconds
            or now - document["created"] >= self.settings.limits.lifetime_seconds
        ):
            raise Denied("session_not_found")

    def create(self, principal, sid):
        now = self.clock()
        document = SessionDocument(
            schema_version=1,
            session_id=sid,
            owner_ref=scope_ref(principal),
            created=now,
            touched=now,
            revision=0,
            history_epoch=0,
            movie_reads=0,
            memory_operations=0,
            active_run=None,
            active_until=0.0,
            memory_generation=None,
            messages=[],
        ).model_dump()
        self.backend.create(self.key(principal, sid), document)
        return document

    def load(self, principal, sid):
        document = self.backend.read(self.key(principal, sid))
        self._live(document)
        return document

    def claim(self, principal, sid, revision, run_id, *, memory=False, charge_memory=True):
        def transition(document):
            self._live(document)
            if document["revision"] != revision:
                raise Denied("stale_revision")
            now = self.clock()
            if document["active_run"] is not None and document["active_until"] > now:
                raise Denied("busy")
            if memory and charge_memory:
                if document["memory_operations"] >= 8:
                    raise Denied("memory_budget")
                document["memory_operations"] += 1
            document["active_run"] = run_id
            document["active_until"] = now + self.settings.limits.run_seconds
            document["touched"] = now
            return copy.deepcopy(document)

        return self.backend.transact(self.key(principal, sid), transition)

    def fence(self, principal, sid, revision, run_id):
        document = self.load(principal, sid)
        if (
            document["revision"] != revision
            or document["active_run"] != run_id
            or self.clock() >= document["active_until"]
        ):
            raise Denied("session_changed")
        return document

    def charge(self, principal, sid, revision, run_id, counter, amount=1):
        if (
            counter not in {"movie_reads", "memory_operations"}
            or type(amount) is not int
            or amount < 1
        ):
            raise Denied("session_backend_invalid")
        limit = self.settings.limits.turns if counter == "movie_reads" else 8

        def transition(document):
            self._live(document)
            if document["revision"] != revision or document["active_run"] != run_id:
                raise Denied("session_changed")
            if document[counter] + amount > limit:
                raise Denied("tool_budget" if counter == "movie_reads" else "memory_budget")
            document[counter] += amount
            return document[counter]

        return self.backend.transact(self.key(principal, sid), transition)

    def commit(
        self,
        principal,
        sid,
        revision,
        run_id,
        *,
        messages=None,
        memory_generation=None,
        advance=True,
        history_epoch=1,
    ):
        def transition(document):
            self._live(document)
            if (
                document["revision"] != revision
                or document["active_run"] != run_id
                or self.clock() >= document["active_until"]
            ):
                raise Denied("session_changed")
            if messages is not None:
                document["messages"] = messages
                document["history_epoch"] = history_epoch
                document["memory_generation"] = memory_generation
            document["revision"] += int(advance)
            document["active_run"] = None
            document["active_until"] = 0.0
            document["touched"] = self.clock()
            SessionDocument.model_validate(document)
            return copy.deepcopy(document)

        return self.backend.transact(self.key(principal, sid), transition)

    def abandon(self, principal, sid, run_id):
        def transition(document):
            if document["active_run"] == run_id:
                document["active_run"] = None
                document["active_until"] = 0.0
            return None

        return self.backend.transact(self.key(principal, sid), transition)

    def reset(self, principal, sid, *, clear=True):
        def transition(document):
            self._live(document)
            old_run = document["active_run"]
            document["revision"] += 1
            document["active_run"] = None
            document["active_until"] = 0.0
            document["touched"] = self.clock()
            if clear:
                document["messages"] = []
                document["memory_generation"] = None
            return copy.deepcopy(document), old_run

        return self.backend.transact(self.key(principal, sid), transition)

    def close(self):
        self.backend.close()
