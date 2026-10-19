"""Governed preference contracts, shared state transitions, and the local test adapter.

No model memory tools, transcript saving, or automatic recall are enabled here.
"""

import hashlib
import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .model import Denied

PURPOSE = "movie_preferences"
OPERATIONS = frozenset({"inspect", "save", "correct", "forget", "forget_all"})
VALUES = {
    "preferred_genre": frozenset(
        {"action", "animation", "comedy", "documentary", "drama", "science_fiction"}
    ),
    "preferred_language": frozenset({"en", "es", "fr", "ja"}),
}


class Preference(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    category: Literal["preferred_genre", "preferred_language"]
    value: str = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def approved_value(self):
        if self.value not in VALUES[self.category]:
            raise ValueError("unapproved preference value")
        return self


@dataclass(frozen=True)
class MemoryPolicy:
    """Explicit fixture policy; no default constitutes a product/retention approval."""

    version: str
    scope: Literal["session", "user"]
    retention_seconds: int
    max_records: int
    operations_per_session: int

    def __post_init__(self):
        if (
            not isinstance(self.version, str)
            or not 1 <= len(self.version) <= 100
            or self.scope not in {"session", "user"}
            or type(self.retention_seconds) is not int
            or not 1 <= self.retention_seconds <= 31536000
            or type(self.max_records) is not int
            or not 1 <= self.max_records <= 10
            or type(self.operations_per_session) is not int
            or not 1 <= self.operations_per_session <= 32
        ):
            raise ValueError("invalid memory policy")


@dataclass(frozen=True)
class MemoryAccess:
    """Constructed by trusted orchestration from verified identity/session ownership."""

    tenant: str
    user: str
    session: str
    origin: Literal["user", "skill"]
    operations: frozenset[str]

    def partition(self, policy):
        if (
            any(
                not isinstance(v, str) or not 1 <= len(v) <= 128
                for v in (self.tenant, self.user, self.session)
            )
            or self.origin not in {"user", "skill"}
            or not isinstance(self.operations, frozenset)
            or not self.operations <= OPERATIONS
        ):
            raise Denied("memory_forbidden")
        return (self.tenant, self.user, self.session if policy.scope == "session" else "", PURPOSE)


@dataclass(frozen=True)
class MemoryRecord:
    id: str
    category: str
    value: str
    revision: int
    created_at: float
    updated_at: float
    expires_at: float
    source_session: str
    consent_policy: str
    source: str = "explicit_user_preference"
    confidence: str = "user_declared"
    untrusted: bool = True


class PreferenceState:
    """Shared in-memory transition engine, operating on one scoped snapshot.

    There is no broad lookup/query API, network client, derived index, or disk backup.
    Effect records and deletion markers contain no preference values.
    """

    def __init__(self):
        self._partitions = {}
        self._generations = {}
        self._deleted = set()
        self._lock = threading.Lock()
        self.effects = []

    def apply(
        self,
        partition,
        operation,
        *,
        now,
        policy,
        session,
        preference=None,
        record_id=None,
        expected_generation=None,
        expected_revision=None,
    ):
        with self._lock:
            records = self._partitions.setdefault(partition, {})
            for key, record in list(records.items()):
                if record.expires_at <= now:
                    del records[key]
                    self._deleted.add((partition, key))
                    self._generations[partition] = self._generations.get(partition, 0) + 1
            generation = self._generations.get(partition, 0)
            scope_ref = hashlib.sha256(repr(partition).encode()).hexdigest()
            if operation == "inspect":
                self.effects.append((operation, scope_ref))
                return {"generation": generation, "memories": [asdict(r) for r in records.values()]}
            if operation in {"save", "correct"}:
                if type(expected_generation) is not int or expected_generation != generation:
                    raise Denied("memory_conflict")
                if operation == "save":
                    if any(r.category == preference.category for r in records.values()):
                        raise Denied("memory_exists")
                    if len(records) >= policy.max_records:
                        raise Denied("memory_capacity")
                    record = MemoryRecord(
                        str(uuid.uuid4()),
                        preference.category,
                        preference.value,
                        1,
                        now,
                        now,
                        now + policy.retention_seconds,
                        session,
                        policy.version,
                    )
                else:
                    old = records.get(record_id)
                    if old is None:
                        raise Denied("memory_not_found")
                    if type(expected_revision) is not int or expected_revision != old.revision:
                        raise Denied("memory_conflict")
                    if preference.category != old.category:
                        raise Denied("memory_invalid")
                    record = replace(
                        old,
                        value=preference.value,
                        revision=old.revision + 1,
                        updated_at=now,
                        expires_at=now + policy.retention_seconds,
                        source_session=session,
                        consent_policy=policy.version,
                    )
                records[record.id] = record
                result = {"memory": asdict(record)}
            elif operation == "forget":
                if record_id not in records:
                    raise Denied("memory_not_found")
                del records[record_id]
                self._deleted.add((partition, record_id))
                result = {"forgotten": True}
            elif operation == "forget_all":
                self._deleted.update((partition, key) for key in records)
                records.clear()
                result = {"forgotten": True}
            else:
                raise Denied("memory_forbidden")
            self._generations[partition] = generation + 1
            self.effects.append((operation, scope_ref))
            return {**result, "generation": generation + 1}


class FixtureMemoryStore(PreferenceState):
    """Explicitly non-durable RAM adapter for tests. Never enabled by hosted defaults."""


class MemoryService:
    def __init__(self, policy: MemoryPolicy, store, clock=time.time, audit=None):
        from .blob_memory import BlobMemoryStore

        if type(store) not in (FixtureMemoryStore, BlobMemoryStore):
            raise ValueError("only the reviewed local fixture or Blob adapter is supported")
        if type(store) is BlobMemoryStore and audit is None:
            raise ValueError("durable memory requires an explicit audit callback")
        self.policy, self.store, self.clock = policy, store, clock
        self.audit = audit or (lambda _: None)

    def call(
        self,
        access,
        operation,
        *,
        preference=None,
        consent=False,
        record_id=None,
        expected_generation=None,
        expected_revision=None,
    ):
        partition = access.partition(self.policy)
        # Skills can never turn a model's purported approval into write consent.
        if (
            operation not in OPERATIONS
            or operation not in access.operations
            or (access.origin == "skill" and operation != "inspect")
        ):
            raise Denied("memory_forbidden")
        if operation in {"save", "correct"}:
            if consent is not True or access.origin != "user":
                raise Denied("memory_consent_required")
            try:
                preference = Preference.model_validate(preference)
            except ValueError:
                raise Denied("memory_invalid") from None
        event = {
            "event": "memory_operation_authorized",
            "operation": operation,
            "policy": self.policy.version,
            "origin": access.origin,
            "scope_ref": hashlib.sha256(repr(partition).encode()).hexdigest(),
        }
        try:
            self.audit(event)  # Required delivery failure prevents access/effect.
        except Exception:
            raise Denied("audit_unavailable") from None
        return self.store.apply(
            partition,
            operation,
            now=self.clock(),
            policy=self.policy,
            session=access.session,
            preference=preference,
            record_id=record_id,
            expected_generation=expected_generation,
            expected_revision=expected_revision,
        )

    def close(self):
        from .blob_memory import BlobMemoryStore

        if type(self.store) is BlobMemoryStore:
            self.store.close()


def load_memory_policy(path: str) -> MemoryPolicy:
    """Application-owned policy path, never supplied by a chat or API request."""
    return MemoryPolicy(**json.loads(Path(path).read_text()))
