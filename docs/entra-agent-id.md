# Microsoft Entra Agent ID integration

Status: completed for the selected dev deployment, including actual downstream inference/MCP use and cached agent tokens. Stage/prod rollout is separate. This is an additional Stage 5 release requirement.

## Identity paths before integration

Before this integration, the Container Apps agent authenticated downstream using Azure managed identities. `model.py`, `movie_mcp.py`, `blob_memory.py`, `skill_control.py` and `control_telemetry.py` acquire managed-identity credentials. The API and CLI have separate Entra application registrations for incoming user authentication. None of these facts establishes that the agent has an Entra Agent ID blueprint or uses an agent identity.

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


## Dev implementation checkpoint

Blueprint client ID: `cfb45dee-91b3-498e-b43b-11310e6ef473`. Agent client/object ID: `94a137c6-e4fc-481c-b45d-f2a03d868ba4`. Existing agent system identity is the federated workload credential. The operator-only provisioner defaults to planning and was rerun successfully without duplicate objects. [Provisioning evidence](validation/stage-5-evidence/agent-id-provisioning.json) records identifiers and the scoped Catalog.Read assignment. The separately compiled Foundry access module applies only Foundry User on the existing account.

The credential adapter performs managed identity → blueprint token with `fmi_path` → agent resource token, caches tokens with early refresh and fences resource scopes. It never falls back to workload tokens. A real in-container exchange returned the new agent's `oid` and `appid` for the Cognitive Services audience; a minted token alone is not proof of downstream authorization. The configured runtime uses separate adapter instances for inference and MCP. Blob/control/monitoring/skill infrastructure access remains on workload identity.

Dev GitHub environment variables enable the integration with non-secret identifiers; stage/prod default disabled until their objects and grants are provisioned. The deployed release passed the existing High/Critical security gate. Stage/prod provisioning and expanded governance/licensing are not claimed complete.


## Hosted acceptance

The [dev acceptance report](validation/stage-5-agent-id-observability.md) records the deployed image, real token claims, authorized inference and MCP call, caching, and accounting-preserving recovery. The runtime uses agent tokens for both inference and MCP. Generic Blob/control/telemetry infrastructure access remains on managed identity. Legacy grants are retained for rollback; full permission retirement and governance/revocation rehearsal remain separate Stage 5 identity-review work.
