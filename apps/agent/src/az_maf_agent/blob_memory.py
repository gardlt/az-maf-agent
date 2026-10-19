"""Pinned, managed-identity Blob adapter for one bounded preference document per scope."""

import hashlib
import json
import re
import time
from dataclasses import asdict
from email.utils import formatdate
from typing import Literal

import httpx
from azure.identity import ManagedIdentityCredential
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .memory import MemoryRecord, Preference, PreferenceState
from .model import Denied

MAX_DOCUMENT_BYTES = 16384


class StoredPreference(Preference):
    id: str = Field(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    )
    revision: int = Field(ge=1)
    created_at: float = Field(ge=0, allow_inf_nan=False)
    updated_at: float = Field(ge=0, allow_inf_nan=False)
    expires_at: float = Field(ge=0, allow_inf_nan=False)
    source_session: str = Field(min_length=1, max_length=128)
    consent_policy: str = Field(min_length=1, max_length=100)
    source: Literal["explicit_user_preference"]
    confidence: Literal["user_declared"]
    untrusted: Literal[True]

    @model_validator(mode="after")
    def valid_times(self):
        if not self.created_at <= self.updated_at < self.expires_at:
            raise ValueError("invalid timestamps")
        return self


class Document(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: int = Field(ge=1, le=1)
    scope_ref: str = Field(pattern=r"^[0-9a-f]{64}$")
    generation: int = Field(ge=0)
    records: list[StoredPreference] = Field(max_length=2)

    @model_validator(mode="after")
    def unique_records(self):
        if len({r.id for r in self.records}) != len(self.records) or len(
            {r.category for r in self.records}
        ) != len(self.records):
            raise ValueError("duplicate preferences")
        return self


class BlobMemoryStore:
    """No lists, wildcard writes, arbitrary queries, caching, or unconditional overwrites.

    Empty generation documents are retained after forgetting: deleting the blob itself
    would let a stale create treat the namespace as new. Backup restore needs a separate
    deletion-fencing design before it can be enabled.
    """

    def __init__(self, account: str, container: str, credential=None, http=None):
        if (
            not re.fullmatch(r"[a-z0-9]{3,24}", account)
            or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])", container)
            or "--" in container
        ):
            raise ValueError("invalid approved memory destination")
        self.origin = f"https://{account}.blob.core.windows.net/{container}/movie-preferences-v1/"
        self.credential = credential or ManagedIdentityCredential(
            connection_timeout=3, read_timeout=5, retry_total=0
        )
        self.http = http or httpx.Client(timeout=5.0, follow_redirects=False)

    def _request(self, method, url, *, content=None, conditions=None, control=None):
        started = time.monotonic()
        try:
            if control is not None and control.is_set():
                raise Denied("memory_cancelled")
            token = self.credential.get_token("https://storage.azure.com/.default")
            headers = {
                "Authorization": "Bearer " + token.token,
                "x-ms-version": "2023-11-03",
                "x-ms-date": formatdate(usegmt=True),
            }
            if method == "PUT":
                headers.update({"x-ms-blob-type": "BlockBlob", "Content-Type": "application/json"})
            headers.update(conditions or {})
            if control is not None and control.is_set():
                raise Denied("memory_cancelled")
            with self.http.stream(method, url, headers=headers, content=content) as response:
                body = bytearray()
                for chunk in response.iter_bytes():
                    if time.monotonic() - started > 10 or (
                        control is not None and control.is_set()
                    ):
                        raise Denied("memory_timeout")
                    body.extend(chunk)
                    if len(body) > MAX_DOCUMENT_BYTES:
                        raise Denied("memory_backend_invalid")
                return response.status_code, response.headers, bytes(body)
        except Denied:
            raise
        except Exception:
            # Do not retry an ambiguous PUT; its conditional commit may have succeeded.
            raise Denied("memory_backend_unavailable") from None

    def apply(self, partition, operation, **arguments):
        control = arguments.pop("control", None)
        scope_ref = hashlib.sha256(
            json.dumps(partition, separators=(",", ":")).encode()
        ).hexdigest()
        url = self.origin + scope_ref + ".json"
        status, headers, content = self._request("GET", url, control=control)
        etag = None
        if status == 404 and headers.get("x-ms-error-code") == "BlobNotFound":
            document = Document(schema_version=1, scope_ref=scope_ref, generation=0, records=[])
        elif status == 200:
            try:
                document = Document.model_validate_json(content)
                etag = headers["etag"]
                policy = arguments["policy"]
                if (
                    document.scope_ref != scope_ref
                    or not re.fullmatch(r'"[^"\r\n]{1,100}"', etag)
                    or len(document.records) > policy.max_records
                    or any(
                        r.consent_policy != policy.version
                        or r.expires_at - r.updated_at > policy.retention_seconds
                        for r in document.records
                    )
                ):
                    raise ValueError("invalid document binding")
            except (ValueError, KeyError):
                raise Denied("memory_backend_invalid") from None
        else:
            raise Denied("memory_backend_unavailable")
        # Replay the shared policy transition against a private, validated snapshot.
        # Only the conditional Blob PUT commits it; this temporary engine is discarded.
        engine = PreferenceState()
        engine._partitions[partition] = {
            r.id: MemoryRecord(**r.model_dump()) for r in document.records
        }
        engine._generations[partition] = document.generation
        result = engine.apply(partition, operation, **arguments)
        generation = engine._generations[partition]
        if generation != document.generation:
            records = [asdict(r) for r in engine._partitions[partition].values()]
            updated = Document.model_validate(
                {
                    "schema_version": 1,
                    "scope_ref": scope_ref,
                    "generation": generation,
                    "records": records,
                }
            )
            payload = updated.model_dump_json().encode()
            if len(payload) > MAX_DOCUMENT_BYTES:
                raise Denied("memory_backend_invalid")
            conditions = {"If-Match": etag} if etag else {"If-None-Match": "*"}
            status, _, _ = self._request(
                "PUT", url, content=payload, conditions=conditions, control=control
            )
            if status in (409, 412):
                raise Denied("memory_conflict")
            if status != 201:
                raise Denied("memory_backend_unavailable")
        return result

    def close(self):
        self.http.close()
        self.credential.close()
