"""Shared atomic run accounting and operator-owned containment policy.

Backends own persistence and policy authorization. The pure transition layer never
accepts model-supplied identity, pricing, approvals, or operator authority.
"""

import copy
import hashlib
import json
import re
import threading
import time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .model import Denied

CAPABILITIES = frozenset(
    {
        "model",
        "mcp:movies",
        "tool:search_movies",
        "tool:get_movie",
        "skill:movie-night",
        "skill:movie-research",
        "memory:read",
        "memory:write",
        "simulation:credit",
    }
)


class ControlPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    schema_version: int = Field(ge=1, le=1)
    epoch: int = Field(ge=1)
    global_stop: bool
    disabled: list[str] = Field(max_length=20)
    poll_seconds: float = Field(gt=0, le=2)
    containment_seconds: float = Field(gt=0, le=10)
    lease_seconds: float = Field(gt=0, le=30)
    audit_retention_days: int = Field(ge=30, le=30)
    violation_limit: int = Field(ge=1, le=3)

    @field_validator("disabled")
    @classmethod
    def known_capabilities(cls, value):
        if len(value) != len(set(value)) or not set(value) <= CAPABILITIES:
            raise ValueError("unknown or duplicate capability")
        return value


def scope_ref(principal):
    return hashlib.sha256(
        json.dumps([principal.tenant, principal.user], separators=(",", ":")).encode()
    ).hexdigest()


def empty_state():
    return {
        "schema_version": 1,
        "policy_epoch": 1,
        "runs": {},
        "daily": {},
        "receipts": {},
        "sessions": {},
    }


class FixtureControlBackend:
    """Independent clients can share this fixture; operator methods are separate."""

    def __init__(self, policy):
        self._policy = policy
        self._state = empty_state()
        self._lock = threading.RLock()
        self.events = []
        self.available = True
        self._approvals = {}

    def policy(self):
        if not self.available:
            raise Denied("control_unavailable")
        return self._policy.model_copy(deep=True)

    def transact(self, transition):
        if not self.available:
            raise Denied("control_unavailable")
        with self._lock:
            state = copy.deepcopy(self._state)
            result = transition(state)
            self._state = state
            return copy.deepcopy(result)

    def snapshot(self):
        if not self.available:
            raise Denied("control_unavailable")
        with self._lock:
            return copy.deepcopy(self._state)

    def audit(self, event):
        if not self.available:
            raise Denied("audit_unavailable")
        self.events.append(copy.deepcopy(event))

    def read_approval(self, approval_id):
        if approval_id not in self._approvals:
            raise Denied("approval_required")
        return self._approvals[approval_id]

    def close(self):
        pass


class FixtureOperator:
    def __init__(self, backend):
        self.backend = backend

    def publish(self, expected_epoch, *, stop=None, disabled=None, recover=False):
        with self.backend._lock:
            current = self.backend.policy()
            if current.epoch != expected_epoch:
                raise Denied("control_conflict")
            if current.global_stop and stop is False and not recover:
                raise Denied("explicit_recovery_required")
            update = current.model_dump() | {"epoch": current.epoch + 1}
            if stop is not None:
                update["global_stop"] = stop
            if disabled is not None:
                update["disabled"] = disabled
            self.backend._state["policy_epoch"] = update["epoch"]
            self.backend._policy = ControlPolicy.model_validate(update)
            return self.backend._policy


class RunControls:
    def __init__(self, backend, settings, clock=time.time):
        self.backend, self.settings, self.clock = backend, settings, clock
        self.highest_epoch = 0

    def policy(self):
        policy = self.backend.policy()
        if policy.epoch < self.highest_epoch:
            raise Denied("control_rollback")
        self.highest_epoch = policy.epoch
        return policy

    def _event(self, event, run_id, epoch, **metadata):
        self.backend.audit(
            {"event": event, "run_id": run_id, "epoch": epoch, "time": self.clock(), **metadata}
        )

    def inspect(self, principal, run_id):
        record = self.backend.snapshot()["runs"].get(run_id)
        if record is None or record["owner"] != scope_ref(principal):
            raise Denied("run_not_found")
        return {key: value for key, value in record.items() if key != "owner"}

    def register_session(self, principal, sid):
        policy = self.policy()
        if policy.global_stop:
            raise Denied("global_stop")
        self._event(
            "session_admission_authorized", sid, policy.epoch, scope_ref=scope_ref(principal)
        )

        def transition(state):
            now = self.clock()
            if policy.epoch < state["policy_epoch"]:
                raise Denied("control_rollback")
            state["policy_epoch"] = policy.epoch
            state["sessions"] = {
                key: value for key, value in state["sessions"].items() if value["expires_at"] > now
            }
            if (
                sid in state["sessions"]
                or len(state["sessions"]) >= self.settings.limits.max_sessions
            ):
                raise Denied("session_capacity")
            state["sessions"][sid] = {
                "owner": scope_ref(principal),
                "expires_at": now + self.settings.limits.lifetime_seconds,
            }
            return None

        return self.backend.transact(transition)

    def start(self, principal, run_id):
        if not re.fullmatch(r"[0-9a-f-]{36}", run_id):
            raise Denied("invalid_run")
        policy, owner = self.policy(), scope_ref(principal)
        if policy.global_stop:
            raise Denied("global_stop")
        self._event("run_admission_authorized", run_id, policy.epoch, scope_ref=owner)
        limits = self.settings.limits

        def transition(state):
            now = self.clock()
            if policy.epoch < state["policy_epoch"]:
                raise Denied("control_rollback")
            state["policy_epoch"] = policy.epoch
            if run_id in state["runs"]:
                raise Denied("run_replay")
            live = [
                r
                for r in state["runs"].values()
                if r.get("unresolved", False)
                or (r["status"] == "active" and r["lease_until"] > now and r["deadline"] > now)
            ]
            if (
                len(live) >= limits.parallel
                or sum(r["owner"] == owner for r in live) >= limits.per_user_parallel
            ):
                raise Denied("shared_concurrency")
            # Retain terminal runs for the maximum run lifetime; counters live separately.
            state["runs"] = {
                key: r
                for key, r in state["runs"].items()
                if r.get("unresolved", False) or r["deadline"] + 86400 > now
            }
            if len(state["runs"]) >= 1000:
                raise Denied("control_capacity")
            state["runs"][run_id] = {
                "owner": owner,
                "epoch": policy.epoch,
                "status": "active",
                "deadline": now + limits.run_seconds,
                "lease_until": now + policy.lease_seconds,
                "calls": 0,
                "tokens": 0,
                "usd": "0",
                "actual_tokens": 0,
                "tools": 0,
                "memory": 0,
                "violations": 0,
                "cancelled": False,
                "call_receipts": {},
                "unresolved": False,
                "operator_resolution": None,
            }
            state["daily"] = {
                key: value
                for key, value in state["daily"].items()
                if int(key.split(":", 1)[0]) >= int(now // 86400) - 1
            }
            return {"run_id": run_id, "epoch": policy.epoch, "poll_seconds": policy.poll_seconds}

        result = self.backend.transact(transition)
        self._authority(policy.epoch)
        return result

    def _authority(self, epoch, capability=None):
        policy = self.policy()
        if policy.global_stop:
            raise Denied("global_stop")
        if policy.epoch != epoch:
            raise Denied("policy_changed")
        if capability is not None and (
            capability not in CAPABILITIES or capability in policy.disabled
        ):
            raise Denied("capability_disabled")
        return policy

    def _active(self, state, run_id, owner, epoch, now):
        if epoch < state["policy_epoch"]:
            raise Denied("control_rollback")
        run = state["runs"].get(run_id)
        if run is None or run["owner"] != owner:
            raise Denied("run_not_found")
        if run["epoch"] != epoch or run["cancelled"] or run["status"] != "active":
            raise Denied("run_cancelled")
        if now >= run["deadline"] or now >= run["lease_until"]:
            raise Denied("run_lease_expired")
        return run

    def gate(self, principal, run_id, epoch, capability=None, *, count=None, actual_tokens=None):
        policy = self._authority(epoch, capability)
        owner, limits = scope_ref(principal), self.settings.limits
        if count is not None and (
            type(count) is not int or not 0 <= count <= limits.context_tokens
        ):
            raise Denied("context_limit")
        self._event("dispatch_authorized", run_id, epoch, capability=capability, scope_ref=owner)

        def transition(state):
            now = self.clock()
            if epoch < state["policy_epoch"]:
                raise Denied("control_rollback")
            state["policy_epoch"] = epoch
            run = self._active(state, run_id, owner, epoch, now)
            if count is not None:
                if (
                    capability != "model"
                    or self.settings.input_usd_per_million is None
                    or self.settings.output_usd_per_million is None
                ):
                    raise Denied("unknown_pricing")
                total = count + limits.output_tokens
                cost = (
                    Decimal(str(self.settings.input_usd_per_million)) * count
                    + Decimal(str(self.settings.output_usd_per_million)) * limits.output_tokens
                ) / 1_000_000
                key = f"{int(now // 86400)}:{owner}"
                daily = Decimal(state["daily"].get(key, "0")) + cost
                if (
                    run["calls"] >= limits.turns
                    or run["tokens"] + total > limits.run_tokens
                    or Decimal(run["usd"]) + cost > Decimal(str(limits.run_usd))
                ):
                    raise Denied("shared_run_budget")
                if daily > Decimal(str(limits.daily_usd)):
                    raise Denied("shared_daily_budget")
                state["daily"][key] = str(daily)
                run["unresolved"] = True
                run.update(
                    calls=run["calls"] + 1,
                    tokens=run["tokens"] + total,
                    usd=str(Decimal(run["usd"]) + cost),
                )
            if capability and capability.startswith("tool:"):
                if run["tools"] >= limits.turns:
                    raise Denied("shared_tool_budget")
                run["tools"] += 1
            if capability and capability.startswith("memory:"):
                if run["memory"] >= 8:
                    raise Denied("shared_memory_budget")
                run["memory"] += 1
            if actual_tokens is not None:
                if (
                    type(actual_tokens) is not int
                    or actual_tokens < run["actual_tokens"]
                    or actual_tokens > run["tokens"]
                ):
                    raise Denied("provider_usage")
                run["actual_tokens"] = actual_tokens
            run["lease_until"] = min(run["deadline"], now + policy.lease_seconds)
            return copy.deepcopy(run)

        result = self.backend.transact(transition)
        # A policy change racing a successful reservation prevents dispatch, without refund.
        self._authority(epoch, capability)
        return result

    def reconcile(self, principal, run_id, call_number, actual_tokens):
        owner = scope_ref(principal)

        def transition(state):
            run = state["runs"].get(run_id)
            if not run or run["owner"] != owner:
                raise Denied("run_not_found")
            if type(call_number) is not int or not 1 <= call_number <= run["calls"]:
                raise Denied("provider_usage")
            if type(actual_tokens) is not int or not 0 <= actual_tokens <= run["tokens"]:
                raise Denied("provider_usage")
            key = str(call_number)
            old = run["call_receipts"].get(key)
            if old is not None and old != actual_tokens:
                raise Denied("provider_usage")
            run["call_receipts"][key] = actual_tokens
            run["actual_tokens"] = sum(v for v in run["call_receipts"].values() if v is not None)
            if run["actual_tokens"] > run["tokens"]:
                raise Denied("provider_usage")
            run["unresolved"] = (
                len(run["call_receipts"]) != run["calls"] and run["operator_resolution"] is None
            )
            return copy.deepcopy(run)

        return self.backend.transact(transition)

    def reject(self, principal, run_id, call_number, status):
        """Known terminal HTTP rejection; usage is unknown and cost stays reserved."""
        if type(status) is not int or status not in {400, 401, 403, 404, 405, 413, 415, 422, 429}:
            raise Denied("provider_usage")
        owner = scope_ref(principal)
        record = self.inspect(principal, run_id)
        self._event(
            "provider_request_rejected",
            run_id,
            record["epoch"],
            scope_ref=owner,
            status="http_" + str(status),
        )

        def transition(state):
            run = state["runs"].get(run_id)
            if not run or run["owner"] != owner:
                raise Denied("run_not_found")
            if type(call_number) is not int or not 1 <= call_number <= run["calls"]:
                raise Denied("provider_usage")
            key = str(call_number)
            if key in run["call_receipts"] and run["call_receipts"][key] is not None:
                raise Denied("provider_usage")
            state["schema_version"] = 2
            run["call_receipts"][key] = None
            run["unresolved"] = (
                len(run["call_receipts"]) != run["calls"] and run["operator_resolution"] is None
            )
            return copy.deepcopy(run)

        return self.backend.transact(transition)

    def finish(self, principal, run_id, epoch, status):
        if status not in {"completed", "cancelled", "failed"}:
            raise Denied("invalid_run_state")
        owner = scope_ref(principal)
        self._event("run_terminal", run_id, epoch, status=status)

        def transition(state):
            run = state["runs"].get(run_id)
            if run is None or run["owner"] != owner:
                raise Denied("run_not_found")
            run["status"] = status
            return copy.deepcopy(run)

        result = self.backend.transact(transition)
        if result["unresolved"]:
            self._event("unresolved_effect", run_id, epoch, status=status)
            print(
                json.dumps({"event": "control_fault", "category": "unresolved_effect"}), flush=True
            )
        return result

    def cancel(self, principal, run_id):
        owner = scope_ref(principal)

        def transition(state):
            run = state["runs"].get(run_id)
            if run is None or run["owner"] != owner:
                raise Denied("run_not_found")
            run["cancelled"] = True
            return {"cancelled": True}

        return self.backend.transact(transition)
