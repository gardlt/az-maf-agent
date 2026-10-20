# Stage 7 local containment foundation — 2026-10-20

Status: first local implementation slice; Stage 7 remains incomplete and is not deployed.

## Implemented

- `apps/agent/src/az_maf_agent/containment.py`: operator-owned SQLite development store with private creation permissions, per-tenant/Agent-ID registration, quarantine generations, atomic event deduplication/windowed configurable thresholds, incidents and content-free transition records. Quarantine commits before directory I/O; duplicate incidents do not advance generation repeatedly.
- A fixed-origin, disable-only Graph adapter verifies the registered individual Agent ID binding, patches only `accountEnabled=false` and requires disabled readback. Persisted retries are bounded; failures retain quarantine. Directory-disabled status deliberately does not mean resource-contained.
- A read-only quarantine reader can be injected into `RunControls`. It runs before policy/admission/dispatch checks and causes the existing supervisor watchdog to cancel active work. Missing, corrupt or changed state fails closed; reservations and aggregate counters are preserved.
- Local operator `request_disable` and trusted-receiver `signal` are internal Python interfaces, not exposed administrative HTTP endpoints. Caller authentication, authorization and alert attribution must be supplied by the future independent receiver; never invoke these interfaces from model-controlled arguments.

## Actual validation

`uv run --locked pytest -q`: **233 passed** (215 prior tests plus 18 containment cases). `uv run --locked ruff check apps scripts` and `uv run --locked ruff format --check apps scripts` pass.

The containment fixtures cover threshold counting/deduplication, per-agent isolation, stale/future/malformed events, unknown identities, registry rebinding denial, concurrent duplicate operator requests, restart persistence, retry deferral and redaction, missing/corrupt quarantine state, generation fencing, accounting preservation, active-run cancellation, late-worker outcome fencing, wrong Graph type/identity/application/blueprint, redirects, already-disabled idempotency, write denial, timeout and contradictory readback. HTTP uses `httpx.MockTransport`; no Graph token or live request is made.

## Important remaining boundaries

This is a development persistence/transition adapter. It is **not** a separately deployed controller, authenticated alert receiver, hosted durable inbox or independent service-enforcement boundary. SQLite file permissions under one developer account are not isolation from an untrusted runtime with that same OS authority. Operator/runtime OS permissions or a remotely authorized store must be designed before use outside fixtures.

The quarantine reader is explicitly injected in tests; the hosted application has not been configured to use it. The deployment, runtime credentials, managed identities, Blob permissions and existing token cache are unchanged. No Entra identity is disabled by this change. Existing-token and direct-managed-identity bypass remain unproven; no full containment claim is made.

Automatic alert delivery, independent watchdog/controller leases, escalation delivery, resource inventory and enforcement, read-only status endpoints, production store authorization, portal-disable observation and explicitly authorized recovery still require implementation and hosted QA. There is intentionally no re-enable operation in this first slice. The manual emergency action remains the individual-identity Disable action in the Entra admin center; future controller reconciliation must connect that audit/state change to quarantine rather than treating portal disable as complete resource containment.
