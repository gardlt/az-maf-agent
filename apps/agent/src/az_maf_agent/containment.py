"""Local durable containment transitions. No agent-facing mutation endpoint.

SQLite is an operator-owned development adapter, not a hosted security boundary.
Production requires an independently authorized controller/store and service gates.
"""

import sqlite3
import time
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field

from .model import Denied


def identity(tenant, agent):
    return str(UUID(tenant)), str(UUID(agent))


class DetectionRule(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    version: str = Field(pattern=r"^[a-zA-Z0-9_.-]{1,80}$")
    threshold: int = Field(ge=1, le=100)
    window_seconds: int = Field(ge=1, le=300)
    max_age_seconds: int = Field(ge=1, le=300)


class TrustedAlert(BaseModel):
    """Versioned alert body accepted only after transport authentication."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    schema_version: Literal[1]
    alert_id: str
    tenant_id: str
    agent_id: str
    signal: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,79}$")
    observed_at: float = Field(allow_inf_nan=False)

    def model_post_init(self, _context):
        object.__setattr__(self, "alert_id", str(UUID(self.alert_id)))
        tenant, agent = identity(self.tenant_id, self.agent_id)
        object.__setattr__(self, "tenant_id", tenant)
        object.__setattr__(self, "agent_id", agent)


@dataclass(frozen=True)
class AlertPrincipal:
    """Identity produced by the future hosted transport verifier."""

    tenant_id: str
    subject_id: str

    def __post_init__(self):
        object.__setattr__(self, "tenant_id", str(UUID(self.tenant_id)))
        object.__setattr__(self, "subject_id", str(UUID(self.subject_id)))


@dataclass(frozen=True)
class ContainmentResult:
    alert_id: str
    agent_id: str
    state: str
    quarantined: bool
    directory_disabled: bool


class ContainmentStore:
    def __init__(self, path, *, clock=time.time):
        self.path = Path(path).resolve()
        self.clock = clock
        # Exclusive creation avoids silently adopting an unexpected existing file.
        if not self.path.exists():
            self.path.touch(mode=0o600, exist_ok=False)
        with self.transaction() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS agents (
                    tenant TEXT, agent TEXT, blueprint TEXT, app_id TEXT,
                    generation INTEGER NOT NULL, quarantined INTEGER NOT NULL,
                    PRIMARY KEY(tenant,agent));
                CREATE TABLE IF NOT EXISTS signals (
                    tenant TEXT, agent TEXT, event TEXT, rule TEXT, observed REAL,
                    PRIMARY KEY(tenant,agent,event));
                CREATE TABLE IF NOT EXISTS incidents (
                    tenant TEXT, agent TEXT, incident TEXT, state TEXT,
                    attempts INTEGER, next_attempt REAL, code TEXT,
                    PRIMARY KEY(tenant,agent,incident));
                CREATE TABLE IF NOT EXISTS audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant TEXT, agent TEXT, incident TEXT, action TEXT, at REAL);
            """)

    @contextmanager
    def transaction(self):
        with closing(sqlite3.connect(self.path, timeout=2)) as db:
            db.row_factory = sqlite3.Row
            with db:
                db.execute("BEGIN IMMEDIATE")
                yield db

    def register(self, tenant, agent, blueprint, app_id):
        tenant, agent = identity(tenant, agent)
        blueprint, app_id = str(UUID(blueprint)), str(UUID(app_id))
        if agent == blueprint:
            raise ValueError("individual_agent_required")
        with self.transaction() as db:
            current = db.execute(
                "SELECT blueprint,app_id FROM agents WHERE tenant=? AND agent=?", (tenant, agent)
            ).fetchone()
            if current and tuple(current) != (blueprint, app_id):
                raise Denied("containment_registry_conflict")
            db.execute(
                "INSERT OR IGNORE INTO agents VALUES (?,?,?,?,1,0)",
                (tenant, agent, blueprint, app_id),
            )

    def signal(self, tenant, agent, event_id, observed, rule, *, now=None):
        """Trusted receiver only: authenticating/attributing alerts is not this API's job."""
        tenant, agent = identity(tenant, agent)
        event = str(UUID(event_id))
        now = self.clock() if now is None else now
        if type(observed) not in (int, float) or not now - rule.max_age_seconds <= observed <= now:
            raise Denied("containment_signal_time")
        with self.transaction() as db:
            if not db.execute(
                "SELECT 1 FROM agents WHERE tenant=? AND agent=?", (tenant, agent)
            ).fetchone():
                raise Denied("containment_unknown_agent")
            inserted = db.execute(
                "INSERT OR IGNORE INTO signals VALUES (?,?,?,?,?)",
                (tenant, agent, event, rule.version, observed),
            ).rowcount
            if not inserted:
                return False
            count = db.execute(
                "SELECT count(*) FROM signals WHERE tenant=? AND agent=? AND rule=? "
                "AND observed>=? AND observed<=?",
                (tenant, agent, rule.version, now - rule.window_seconds, now),
            ).fetchone()[0]
            if count < rule.threshold:
                return False
            self._quarantine(db, tenant, agent, event, now)
            return True

    def _quarantine(self, db, tenant, agent, incident, now):
        db.execute(
            "UPDATE agents SET generation=generation+1,quarantined=1 "
            "WHERE tenant=? AND agent=? AND quarantined=0",
            (tenant, agent),
        )
        inserted = db.execute(
            "INSERT OR IGNORE INTO incidents VALUES (?,?,?,'pending',0,?,NULL)",
            (tenant, agent, incident, now),
        ).rowcount
        if inserted:
            db.execute(
                "INSERT INTO audit(tenant,agent,incident,action,at) VALUES (?,?,?,'quarantined',?)",
                (tenant, agent, incident, now),
            )

    def request_disable(self, tenant, agent, incident):
        """Operator-only local development path; no recovery/enable operation exists."""
        tenant, agent = identity(tenant, agent)
        incident = str(UUID(incident))
        with self.transaction() as db:
            if not db.execute(
                "SELECT 1 FROM agents WHERE tenant=? AND agent=?", (tenant, agent)
            ).fetchone():
                raise Denied("containment_unknown_agent")
            self._quarantine(db, tenant, agent, incident, self.clock())

    def attempt_disable(self, tenant, agent, incident, directory, *, max_attempts=3):
        """Persist intent before I/O. Retry by reconciliation; never report resource containment."""
        tenant, agent = identity(tenant, agent)
        incident = str(UUID(incident))
        with self.transaction() as db:
            row = db.execute(
                "SELECT i.*,a.blueprint,a.app_id FROM incidents i JOIN agents a "
                "USING(tenant,agent) WHERE tenant=? AND agent=? AND incident=?",
                (tenant, agent, incident),
            ).fetchone()
            if row is None:
                raise Denied("containment_incident_required")
            if row["state"] == "directory_disabled":
                return "directory_disabled"
            if row["attempts"] >= max_attempts or self.clock() < row["next_attempt"]:
                raise Denied("containment_retry_deferred")
            attempt = row["attempts"] + 1
            # Crash/in-flight lease prevents immediate duplicate dispatch from another worker.
            db.execute(
                "UPDATE incidents SET state='disabling',attempts=?,next_attempt=? "
                "WHERE tenant=? AND agent=? AND incident=?",
                (attempt, self.clock() + 30, tenant, agent, incident),
            )
        try:
            directory.disable(tenant, agent, row["blueprint"], row["app_id"])
            state, code = "directory_disabled", None
        except Exception:
            # Never persist arbitrary exception bodies: they may contain tokens/provider content.
            state, code = "containment_failed", "directory_disable_unverified"
        with self.transaction() as db:
            committed = db.execute(
                "UPDATE incidents SET state=?,code=?,next_attempt=? "
                "WHERE tenant=? AND agent=? AND incident=? AND attempts=? AND state='disabling'",
                (state, code, self.clock() + min(60, 2**attempt), tenant, agent, incident, attempt),
            ).rowcount
            if not committed:
                return db.execute(
                    "SELECT state FROM incidents WHERE tenant=? AND agent=? AND incident=?",
                    (tenant, agent, incident),
                ).fetchone()[0]
            db.execute(
                "INSERT INTO audit(tenant,agent,incident,action,at) VALUES (?,?,?,?,?)",
                (tenant, agent, incident, state, self.clock()),
            )
        return state

    def incident_status(self, tenant, agent, incident):
        """Return bounded controller state without provider payloads or identities."""
        tenant, agent = identity(tenant, agent)
        incident = str(UUID(incident))
        with self.transaction() as db:
            row = db.execute(
                "SELECT state,attempts,next_attempt,code FROM incidents "
                "WHERE tenant=? AND agent=? AND incident=?",
                (tenant, agent, incident),
            ).fetchone()
            if row is None:
                return None
            return {
                "state": row["state"],
                "attempts": row["attempts"],
                "next_attempt": row["next_attempt"],
                "code": row["code"],
            }


class ContainmentController:
    """Authenticate-bound alert orchestration; transport and hosting remain separate."""

    def __init__(self, store, directory, *, tenant, senders, rules):
        self.store = store
        self.directory = directory
        self.tenant = str(UUID(tenant))
        self.senders = frozenset(str(UUID(value)) for value in senders)
        self.rules = dict(rules)
        if not self.senders or not self.rules or any(
            not isinstance(name, str) or not isinstance(rule, DetectionRule)
            for name, rule in self.rules.items()
        ):
            raise ValueError("invalid containment controller configuration")

    def receive(self, principal: AlertPrincipal, alert: TrustedAlert):
        """Persist signal/quarantine before directory I/O; duplicate alerts reconcile."""
        if (
            principal.tenant_id != self.tenant
            or alert.tenant_id != self.tenant
            or principal.subject_id not in self.senders
        ):
            raise Denied("containment_alert_forbidden")
        rule = self.rules.get(alert.signal)
        if rule is None:
            raise Denied("containment_signal_unknown")

        triggered = self.store.signal(
            alert.tenant_id,
            alert.agent_id,
            alert.alert_id,
            alert.observed_at,
            rule,
        )
        incident = self.store.incident_status(
            alert.tenant_id, alert.agent_id, alert.alert_id
        )
        if not triggered and incident is None:
            return ContainmentResult(
                alert.alert_id, alert.agent_id, "signal_recorded", False, False
            )

        try:
            state = self.store.attempt_disable(
                alert.tenant_id, alert.agent_id, alert.alert_id, self.directory
            )
        except Denied as exc:
            if exc.code != "containment_retry_deferred":
                raise
            current = self.store.incident_status(
                alert.tenant_id, alert.agent_id, alert.alert_id
            )
            if current is None:
                raise Denied("containment_incident_required") from None
            state = current["state"]
        return ContainmentResult(
            alert.alert_id,
            alert.agent_id,
            state,
            True,
            state == "directory_disabled",
        )


class QuarantineReader:
    """Read-only connection; OS/service authorization must prevent runtime file writes."""

    def __init__(self, path, tenant, agent):
        self.path = Path(path).resolve()
        self.tenant, self.agent = identity(tenant, agent)
        self.generation = None

    def check(self):
        try:
            with closing(
                sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=1)
            ) as db:
                row = db.execute(
                    "SELECT generation,quarantined FROM agents WHERE tenant=? AND agent=?",
                    (self.tenant, self.agent),
                ).fetchone()
            if row is None or row[1] != 0:
                raise Denied("agent_quarantined")
            if self.generation is not None and row[0] != self.generation:
                raise Denied("agent_quarantine_generation")
            self.generation = row[0]
        except (OSError, sqlite3.Error):
            raise Denied("containment_unavailable") from None


class GraphAgentDisabler:
    """Disable-only, fixed Graph origin, exact registered agent type and identity binding."""

    def __init__(self, tenant, credential, *, http=None):
        self.tenant = str(UUID(tenant))
        self.credential = credential
        self.http = http or httpx.Client(timeout=5, follow_redirects=False)

    def disable(self, tenant, agent, blueprint, app_id):
        tenant, agent = identity(tenant, agent)
        if tenant != self.tenant or agent == blueprint:
            raise Denied("containment_target_forbidden")
        token = self.credential.get_token("https://graph.microsoft.com/.default")
        headers = {"Authorization": "Bearer " + token.token}
        url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{agent}/microsoft.graph.agentIdentity"

        def read():
            # A typed Graph cast may omit @odata.type/appId by default. Verify type
            # on the base principal, and request blueprint binding on the typed view.
            principal_url = url.removesuffix("/microsoft.graph.agentIdentity")
            principal = self.http.get(
                principal_url + "?$select=id,appId,accountEnabled", headers=headers
            )
            if principal.status_code != 200 or len(principal.content) > 65536:
                raise Denied("containment_directory_read")
            try:
                base = principal.json()
                if (
                    base.get("id") != agent
                    or base.get("appId") != app_id
                    or base.get("@odata.type") != "#microsoft.graph.agentIdentity"
                    or type(base.get("accountEnabled")) is not bool
                ):
                    raise Denied("containment_directory_binding")
            except (ValueError, AttributeError):
                raise Denied("containment_directory_read") from None
            response = self.http.get(
                url + "?$select=id,agentIdentityBlueprintId,accountEnabled", headers=headers
            )
            if response.status_code != 200 or len(response.content) > 65536:
                raise Denied("containment_directory_read")
            try:
                data = response.json()
                if (
                    data.get("id") != agent
                    or data.get("agentIdentityBlueprintId") != blueprint
                    or type(data.get("accountEnabled")) is not bool
                    or data["accountEnabled"] != base["accountEnabled"]
                ):
                    raise Denied("containment_directory_binding")
                return data["accountEnabled"]
            except (ValueError, AttributeError):
                raise Denied("containment_directory_read") from None

        if read():
            response = self.http.patch(url, headers=headers, json={"accountEnabled": False})
            if response.status_code != 204:
                raise Denied("containment_directory_write")
        if read():
            raise Denied("containment_disable_unverified")

    def close(self):
        self.http.close()
