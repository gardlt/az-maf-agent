"""Pinned Blob control adapter: policy Reader, state Writer, immutable audit Writer."""

import hashlib
import json
import re
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .blob_memory import BlobMemoryStore
from .guardrails import ControlPolicy
from .model import Denied

MAX_STATE_BYTES = 1048576
UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"


class RunDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    owner: str = Field(pattern=r"^[0-9a-f]{64}$")
    epoch: int = Field(ge=1)
    status: Literal["active", "completed", "cancelled", "failed"]
    deadline: float = Field(ge=0, allow_inf_nan=False)
    lease_until: float = Field(ge=0, allow_inf_nan=False)
    calls: int = Field(ge=0, le=8)
    tokens: int = Field(ge=0, le=24000)
    usd: str = Field(max_length=40)
    actual_tokens: int = Field(ge=0, le=24000)
    tools: int = Field(ge=0, le=8)
    memory: int = Field(ge=0, le=8)
    violations: int = Field(ge=0)
    cancelled: bool
    call_receipts: dict[str, int | None] = Field(max_length=8)
    unresolved: bool
    operator_resolution: Literal["contained_unknown_usage"] | None

    @model_validator(mode="after")
    def consistent_usage(self):
        if any(key not in {str(n) for n in range(1, self.calls + 1)} for key in self.call_receipts):
            raise ValueError("invalid call receipt")
        if any(
            value is not None and not 0 <= value <= self.tokens
            for value in self.call_receipts.values()
        ):
            raise ValueError("invalid call usage")
        if (
            sum(value for value in self.call_receipts.values() if value is not None)
            != self.actual_tokens
            or self.actual_tokens > self.tokens
        ):
            raise ValueError("invalid usage total")
        if self.unresolved != (
            len(self.call_receipts) != self.calls and self.operator_resolution is None
        ):
            raise ValueError("invalid unresolved state")
        return self

    @field_validator("usd")
    @classmethod
    def bounded_decimal(cls, value):
        from decimal import Decimal, InvalidOperation

        try:
            number = Decimal(value)
            if not number.is_finite() or not 0 <= number <= 5:
                raise ValueError("invalid amount")
        except InvalidOperation:
            raise ValueError("invalid amount") from None
        return value


class ReceiptDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    receipt_id: str = Field(pattern=UUID_PATTERN)
    approval_id: str = Field(pattern=UUID_PATTERN)
    argument_ref: str = Field(pattern=r"^[0-9a-f]{64}$")
    scope_ref: str = Field(pattern=r"^[0-9a-f]{64}$")
    run_id: str = Field(pattern=UUID_PATTERN)
    epoch: int = Field(ge=1)
    units: int = Field(ge=1, le=10)
    time: float = Field(ge=0, allow_inf_nan=False)
    status: Literal["committed"]


class SessionRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    owner: str = Field(pattern=r"^[0-9a-f]{64}$")
    expires_at: float = Field(ge=0, allow_inf_nan=False)


class SharedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: int = Field(ge=1, le=2)
    policy_epoch: int = Field(ge=1)
    runs: dict[str, RunDocument] = Field(max_length=1000)
    daily: dict[str, str] = Field(max_length=2000)
    receipts: dict[str, ReceiptDocument] = Field(max_length=1000)
    sessions: dict[str, SessionRegistration] = Field(max_length=1000)

    @model_validator(mode="after")
    def receipt_version(self):
        if self.schema_version == 1 and any(
            value is None for run in self.runs.values() for value in run.call_receipts.values()
        ):
            raise ValueError("nullable usage requires control schema 2")
        return self

    @field_validator("runs")
    @classmethod
    def run_keys(cls, values):
        if any(not re.fullmatch(UUID_PATTERN, key) for key in values):
            raise ValueError("invalid run key")
        return values

    @field_validator("daily")
    @classmethod
    def daily_values(cls, values):
        for key, value in values.items():
            if not re.fullmatch(r"[0-9]{1,10}:[0-9a-f]{64}", key):
                raise ValueError("invalid quota key")
            RunDocument.bounded_decimal(value)
        return values


class BlobControlBackend:
    def __init__(self, account, *, credential=None, telemetry=None):
        self.telemetry = telemetry
        self.account = account
        self.policy_store = BlobMemoryStore(account, "guardrail-policy", credential=credential)
        self.state_store = BlobMemoryStore(account, "guardrail-state", credential=credential)
        self.audit_store = BlobMemoryStore(account, "guardrail-audit", credential=credential)
        self.policy_url = self.base(self.policy_store) + "policy/current.json"
        self.state_url = self.base(self.state_store) + "state/current.json"

    @staticmethod
    def base(store):
        return store.origin.rsplit("/movie-preferences-v1/", 1)[0] + "/"

    @staticmethod
    def etag(headers):
        value = headers.get("etag", "")
        if not re.fullmatch(r'"[^"\r\n]{1,100}"', value):
            raise Denied("control_invalid")
        return value

    def policy(self):
        status, _, body = self.request(self.policy_store, "GET", self.policy_url)
        if status != 200:
            raise Denied("control_unavailable")
        try:
            return ControlPolicy.model_validate_json(body)
        except ValueError:
            raise Denied("control_invalid") from None

    @staticmethod
    def request(store, *args, **kwargs):
        try:
            return store._request(*args, **kwargs)
        except Denied:
            raise Denied("control_unavailable") from None

    def snapshot(self):
        return self._snapshot()[0]

    def _snapshot(self):
        status, headers, body = self.request(
            self.state_store, "GET", self.state_url, max_bytes=MAX_STATE_BYTES
        )
        if status == 404 and headers.get("x-ms-error-code") == "BlobNotFound":
            raise Denied("control_state_missing")
        if status != 200:
            raise Denied("control_unavailable")
        try:
            state = SharedDocument.model_validate_json(body).model_dump()
        except ValueError:
            raise Denied("control_invalid") from None
        return state, self.etag(headers)

    def transact(self, transition):
        for attempt in range(3):
            state, etag = self._snapshot()
            result = transition(state)
            try:
                payload = SharedDocument.model_validate(state).model_dump_json().encode()
            except ValueError:
                raise Denied("control_invalid") from None
            if len(payload) > MAX_STATE_BYTES:
                raise Denied("control_capacity")
            status, _, _ = self.request(
                self.state_store,
                "PUT",
                self.state_url,
                content=payload,
                conditions={"If-Match": etag},
            )
            if status in (409, 412):
                if attempt == 2:
                    raise Denied("control_conflict")
                continue  # Confirmed non-commit only; rerun all checks on fresh state.
            if status != 201:
                raise Denied("control_unavailable")
            return result  # Never retry a lost/ambiguous response.

    def audit(self, event):
        allowed = {
            "event",
            "run_id",
            "epoch",
            "time",
            "scope_ref",
            "capability",
            "model_route",
            "status",
            "operator_ref",
            "evidence_ref",
        }
        if (
            not set(event) <= allowed
            or len(json.dumps(event)) > 2048
            or event.get("model_route") not in (None, "routine", "reasoning")
        ):
            raise Denied("audit_invalid")
        content = json.dumps(event, sort_keys=True, separators=(",", ":")).encode()
        envelope = json.dumps(
            {"event": event, "sha256": hashlib.sha256(content).hexdigest()}, separators=(",", ":")
        ).encode()
        status, _, _ = self.request(
            self.audit_store,
            "PUT",
            self.base(self.audit_store) + "events/" + str(uuid.uuid4()) + ".json",
            content=envelope,
            conditions={"If-None-Match": "*"},
        )
        if status != 201:
            raise Denied("audit_unavailable")

        if self.telemetry is not None:
            try:
                self.telemetry.record(event)
            except Exception:
                pass  # Export is supplemental; durable protected audit above is mandatory.

    def read_approval(self, approval_id):
        if not re.fullmatch(UUID_PATTERN, approval_id):
            raise Denied("approval_invalid")
        status, _, body = self.request(
            self.policy_store,
            "GET",
            self.base(self.policy_store) + "approvals/" + approval_id + ".json",
        )
        if status != 200:
            raise Denied("approval_required")
        return body

    def close(self):
        if self.telemetry is not None:
            self.telemetry.close()
        for store in (self.policy_store, self.state_store, self.audit_store):
            store.close()
