# 07 — Identity, authentication and least privilege

**Review scope:** caller, agent, workload, service, deployment and operator identities. **Status:** dev Entra Agent ID is integrated with actual downstream token use; full retirement/revocation/governance acceptance remains open.

## Identity is not one credential

| Principal or credential | Intended use | Explicit separation |
| --- | --- | --- |
| CLI user's Entra token | Authenticate approved user to agent API; derive session/memory scope | Not forwarded to MCP, TMDB or Foundry |
| Entra Agent ID | Cognitive Services inference and Catalog.Read MCP tokens | No operator, provisioning or policy-write authority |
| Agent Container App workload identity | Federated starting credential; scoped Blob, skill-control and monitoring access | Infrastructure identity is not silently substituted for agent tokens |
| MCP service and TMDB read token | Service runtime and bounded TMDB GET calls | TMDB token stays at MCP; no user-session/write tool |
| Image-pull identity | ACR image pull | Does not provision agent identities or grant policy |
| Cleanup workload identity | Bounded preference/session cleanup | Separate from model-facing actions |
| GitHub OIDC deployment identity | Reviewed environment deployment and image push | Directory and privileged RBAC bootstrap are separate operator tasks |
| Independent operator | Policy, approvals, reconciliation and Azure platform stop | Unavailable through model tools/API |

## Token flows and resource authority

Incoming Easy Auth/application validation verifies the expected user issuer/audience/tenant and allowed owner scope. An encrypted OS-user-scoped CLI cache supports silent refresh when Entra permits it; login is not promised to last indefinitely. Wrong-audience, invalid/expired credentials cannot be replaced by forged headers.

For downstream Agent ID, the runtime exchanges the federated managed-identity credential through the reviewed blueprint path, then obtains resource-specific agent tokens. Separate adapters constrain Cognitive Services and MCP audiences and cache tokens with early refresh. There is no silent fallback to the old workload token when agent acquisition fails.

The selected dev agent has **Foundry User** on the existing inference account and **Catalog.Read** on the MCP API. Those are distinct permissions on different resources. Agent ID does not automatically authorize memory; Blob/control/telemetry remain workload-identity infrastructure access. The MCP independently validates the expected agent object and role, not just the existence of an Entra token.

## Evidence, lifecycle and limits

**E07** includes actual deployed selected token claims for both downstream audiences, observed cache reuse, successful inference/MCP use and correlated runs. It does not store raw tokens. Provisioning reruns reused directory objects. Actual non-secret IDs are in that inventory; names are not substituted for immutable object IDs.

Some legacy workload grants remain for controlled rollback. Therefore the permission estate is not yet a fully retired minimal set. Token lifetime and revocation propagation need explicit exercises; disabling an identity cannot be claimed to invalidate every already-issued token instantly. Agent registration/visibility does not establish Agent 365, Conditional Access, risk detection, all licensing entitlements or audit-review governance.

Review **R02** for hosted distinct users and **R05/R08** for revocation/rotation, legacy-grant disposition, RBAC re-inventory and separate stage/prod provisioning. Production deployment identities, environment approvals and sponsors/owners require actual platform evidence and named human accountability.

## Source and evidence references

- [Agent ID implementation and inventory](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/entra-agent-id.md)
- [Hosted token-use/cache acceptance](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/validation/stage-5-agent-id-observability.md)
- [Selected deployed token claims, no raw tokens](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/validation/stage-5-evidence/agent-id-runtime-token-claims.json)
- [Resource-scoped credential adapter](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/apps/agent/src/az_maf_agent/agent_identity.py)
- [Provisioning evidence](https://github.com/gardlt/az-maf-agent/blob/d65b5fc480a6eb8e593ac9fe0fd020dffd644b50/docs/validation/stage-5-evidence/agent-id-provisioning.json)

Related: [review index](README.md), [evidence register](09-evidence-register.md), [open review gates](10-review-gaps.md).

## Stage 7 live revocation addendum — 2026-10-20

The [individual-agent containment review](14-agent-containment.md) records a user-authorized dev disable/restore drill. Disabled directory readback was verified, and new Foundry/MCP token requests eventually returned AADSTS7000112. Cached Agent ID tokens still authorized Foundry model listing and MCP tool discovery; Blob metadata access with the separate workload identity also succeeded. Therefore identity disable does not yet satisfy all-resource containment. Restoration and fresh token recovery passed; the ordinary chat canary was budget-blocked. [E13–E15](09-evidence-register.md) retain local tests, live observations and restoration/cleanup evidence. Broader isolation, legacy grants and independent service enforcement remain open.
