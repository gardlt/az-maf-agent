# Microsoft Entra Agent ID integration

Status: required by the user; design recorded, not provisioned or integrated. This is an additional Stage 5 release requirement.

## Current identity paths

The Container Apps agent currently authenticates downstream using Azure managed identities. `model.py`, `movie_mcp.py`, `blob_memory.py`, `skill_control.py` and `control_telemetry.py` acquire managed-identity credentials. The API and CLI have separate Entra application registrations for incoming user authentication. None of these facts establishes that the agent has an Entra Agent ID blueprint or uses an agent identity.

## Proposed environment boundaries

Use one blueprint and one initial agent identity per environment, keeping ownership, permissions and lifecycle changes isolated:

| Environment | Blueprint display name | Agent identity display name |
| --- | --- | --- |
| dev | bp-maf-agent-dev | agent-maf-dev |
| stage | bp-maf-agent-stage | agent-maf-stage |
| prod | bp-maf-agent-prod | agent-maf-prod |

Names are proposals; record actual directory object IDs and application IDs separately. Do not derive one from the other. Require a verified human sponsor and an explicitly selected owner. Directory provisioning uses Microsoft Graph and its Agent ID permissions; Azure subscription Contributor is not evidence of directory authorization. Keep directory setup separate from the normal app deployment identity. Bicep continues to own Azure resources and scoped role assignments.

Use a dedicated workload managed identity as a federated credential for the blueprint. Do not reuse the image-pull/MCP identity as an agent provisioner. Prefer federation over new client secrets. Verify the current supported token exchange or Agent ID SDK integration before implementation; do not substitute an ordinary managed-identity access token while claiming agent authentication.

## Implementation and acceptance

- Inventory existing tenant blueprints and agent identities before creating anything; provisioning must be repeatable without duplicate objects.
- Verify tenant prerequisites and the operator's Graph scopes. Prepare exact blueprint, principal, sponsor/owner, federation and agent identity changes before requesting any missing administrative consent.
- Implement a reproducible directory provisioning command with a read-only plan mode. Persist only identifiers in environment configuration; no tokens or credential values in source, reports or workflow output.
- Introduce a narrow credential adapter for agent-identity token acquisition. Start with dev and verify the downstream token identity without storing raw tokens. Assess Foundry, MCP and Blob support individually before moving their permissions.
- Preserve the existing API/CLI authentication and cached user login. An outbound agent identity does not automatically replace inbound user authentication or require an agent user account.
- Grant only reviewed downstream permissions. Retain the user's required Foundry User role for inference where supported; independently verify resource/provider compatibility. Do not grant the runtime blueprint provisioning or operator policy-write authority.
- Verify authorized inference and MCP reads, forbidden writes, wrong-audience rejection, isolation between environments, and identity disable/revocation. Record directory sign-in/audit evidence and the limits of access-token lifetime and revocation propagation.
- Test restart and token refresh without new client secrets or interactive runtime login. Preserve Stage 5 policy, budgets, required audit and independent operator containment throughout migration.
- Validate rollback before removing old workload grants. Creating an agent identity without using it for the required downstream calls does not pass acceptance.

Agent ID creation and advanced governance have different licensing prerequisites. Verify tenant entitlements for each selected feature; do not claim Conditional Access, risk detection or Agent 365 governance is enabled simply because an identity exists.

## Microsoft references

- [Microsoft Entra Agent ID overview](https://learn.microsoft.com/en-us/entra/agent-id/what-is-microsoft-entra-agent-id)
- [Create a blueprint, configure federation and create its principal](https://learn.microsoft.com/en-us/entra/agent-id/create-blueprint)
- [Agent identities, service principals and applications](https://learn.microsoft.com/en-us/entra/agent-id/agent-service-principals)

## Related observability requirement

[Azure Monitor Agents view](azure-monitor-agents-view.md) is a separate required integration. Directory identity provisioning and runtime agent observability each require their own hosted validation.
