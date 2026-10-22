# Stage 7 controller contract — first implementation slice

Status: local controller orchestration implemented; hosted transport, shared storage,
resource gates, permissions and recovery remain open.

The first controller slice lives in `az_maf_agent.containment`. It establishes the
transition that a hosted alert receiver must preserve:

1. A transport verifier authenticates the caller and constructs an `AlertPrincipal`.
2. `ContainmentController` binds that principal and alert to one configured tenant and
   an explicit sender allowlist.
3. The controller selects a versioned `DetectionRule` from operator configuration.
   Alert content cannot supply its own threshold or window.
4. `ContainmentStore.signal` validates freshness, deduplicates the alert and persists
   quarantine before any Microsoft Graph operation.
5. The exact registered Agent ID is disabled through `GraphAgentDisabler`, with typed
   identity checks and disabled-state readback.
6. Re-delivery of the same triggering alert reconciles the existing incident. A failed
   or deferred Graph call leaves the agent quarantined.

The response is deliberately narrow: signal recorded, disabling, containment failed,
or directory disabled. `directory_disabled` means only that the individual Entra Agent
ID was disabled and read back. It must never be presented as proof that cached tokens,
managed identities, open sessions or every resource path are denied.

## Hosted boundaries still required

The next hosted slice needs an Entra-protected ingress whose verifier fixes the tenant,
issuer, audience and accepted application identities before creating `AlertPrincipal`.
The agent runtime must have no credential or role that can call this ingress, mutate
the registry, write quarantine state or recover an incident.

SQLite remains a local development adapter. The hosted design needs durable shared
state with conditional writes, monotonic generation, an append-only audit trail and a
watchdog/replay path. Alert acknowledgement must follow quarantine persistence.

The controller also needs a reviewed permission manifest. Microsoft Graph authority
must be separated from recovery authority and constrained as far as the platform
supports. Any unavoidable tenant-wide Graph permission requires an explicit risk
decision plus an application registry that refuses unapproved targets before a write.

Resource enforcement remains the critical open gate. Foundry, MCP, Blob and any other
credential path need independent quarantine checks or isolated resources that reject
previously issued credentials. Deploying this controller contract by itself would not
close the cached-token result from the prior live drill.

No recovery method is exposed by this slice. Recovery design must bind an explicit
operator action to the incident and quarantine generation, run isolated canaries, fence
old sessions and queued work, preserve accounting, and release quarantine last.

## Operator notification

The existing Azure Monitor control-fault alert can now attach an Azure Monitor Action
Group when `MAF_ALERT_EMAIL` is supplied to the deployment. The group uses Azure's
common alert schema and sends email for every fired control-fault alert. The dev
receiver is configured at deployment time rather than stored in source. Operators must
confirm the Azure subscription email and exercise the alert before treating delivery
or acknowledgement as an accepted incident-response path. Containment-specific
success, failure and recovery signals still need hosted telemetry before those
transitions can generate distinct notifications.

