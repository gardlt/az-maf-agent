"""Local durable containment transitions. No agent-facing mutation endpoint.

SQLite is an operator-owned development adapter, not a hosted security boundary.
Production requires an independently authorized controller/store and service gates.
"""

import sqlite3
import time
from contextlib import closing, contextmanager
from pathlib import Path
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
            response = self.http.get(url, headers=headers)
            if response.status_code != 200 or len(response.content) > 65536:
                raise Denied("containment_directory_read")
            try:
                data = response.json()
                if (
                    data.get("id") != agent
                    or data.get("appId") != app_id
                    or data.get("agentIdentityBlueprintId") != blueprint
                    or data.get("@odata.type") != "#microsoft.graph.agentIdentity"
                    or type(data.get("accountEnabled")) is not bool
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
