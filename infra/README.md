# Infrastructure architecture

The repository has **two application patterns**, an agent and a movie MCP, sharing resource-level building blocks. **`main.bicep` is the only active environment entry point.** Every environment and optional deployment profile binds to that file.

This is a local implementation of the [resource-module/pattern-module separation](https://learn.microsoft.com/en-us/community/content/azure-verified-modules), not a claim that these custom modules are published or certified Azure Verified Modules.

```text
infra/
  main.bicep                    # target selection, scopes and dependency wiring
  main.bicepparam               # azd environment values
  main.dev.bicepparam            # full dev configuration
  main.stage.bicepparam
  main.prod.bicepparam
  main.*.dev.bicepparam          # optional model/network/storage/access/drill profiles
  modules/                      # resources or closely related parent/child resource families
  patterns/
    agent.bicep                 # agent app, Easy Auth, cleanup job and health rule
    movie-mcp.bicep             # private authenticated movie MCP app
    shared-foundation.bicep    # logs, ACR, pull identity and managed environment
    control-monitoring.bicep   # Insights, fault alert and optional publisher role
    controlled-egress.bicep    # parallel network foundation; no application cutover
    memory-cleanup-monitor.bicep
  fixtures/                     # isolated containment and retired experiments
  tests/resource-contracts.json # pre-refactor security/resource contract baseline
```

Resource modules do not invoke other modules. Application configuration, dependencies and multi-resource composition belong to patterns. `main.bicep` selects patterns/resources and resolves existing shared resources for a targeted deployment. Module reorganization changes ARM deployment-history nesting, not the intended Azure resource names or deterministic role-assignment seeds.

## One entry point, explicit targets

| `deploymentTarget` | Managed resources | Shared/application resources it does not redeploy |
| --- | --- | --- |
| `all` (default) | Shared foundation, both applications and enabled memory/control features | Parallel networking, shared Foundry model and drills remain opt-in |
| `foundation` | Log Analytics, ACR, pull identity and the working managed environment | Applications, memory, controls, Foundry and parallel networking |
| `agent` | Agent app/authentication, plus enabled cleanup job and health rule | MCP, shared foundation/storage and other optional infrastructure |
| `movie-mcp` | MCP application pattern | Agent, cleanup job and shared foundation/storage |
| `memory` | Selected preference account/blob configuration when enabled | Applications and their jobs |
| `controls` | Control containers/retention/lifecycle and monitoring when enabled | Applications and preference account backup configuration |
| `access` | Only explicitly enabled bootstrap role assignments | Ordinary resource deployment and data-plane policy initialization |
| `model` | Configured model deployment in an existing Foundry account/resource group | Existing Foundry account, project and app traffic |
| `network` | Parallel firewall/VNet/environment foundation | Current environment, registry SKU and application traffic |
| `containment` | Explicit isolated synthetic worker | Learner applications |

Targeted updates read existing foundation identifiers rather than recreating the foundation. The pull identity client ID comes from the identity resource, replacing the dev-only literal. Images for unselected services may be empty; selected applications still require valid digest-pinned images and their authenticated configuration.

**Use incremental deployments.** Complete mode with a subset target could delete resources omitted from that target. Conditions are not a deletion strategy. An environment profile is not production-readiness approval; retained acceptance and final-topology gates still apply.

## Environment deployments

The main file is resource-group scoped, preserving the existing least-privilege dev deployment boundary. Create/select the resource group first under an appropriately authorized operator:

```sh
# Bootstrap only, when the resource group does not already exist.
az group create --name rg-maf-dev-eus2-01 --location eastus2

# After supplying reviewed environment variables and both built image digests:
az deployment group what-if --resource-group rg-maf-dev-eus2-01 --parameters infra/main.dev.bicepparam
az deployment group create --resource-group rg-maf-dev-eus2-01 --mode Incremental --parameters infra/main.dev.bicepparam

# Reconcile only the agent pattern; the MCP and foundation are not redeployed.
az deployment group what-if --resource-group rg-maf-dev-eus2-01 --parameters infra/main.dev.bicepparam deploymentTarget=agent
az deployment group create --resource-group rg-maf-dev-eus2-01 --mode Incremental --parameters infra/main.dev.bicepparam deploymentTarget=agent
```

Use the stage/prod profile with its matching group and separately provisioned identities/secrets. Do not reuse the dev caller allowlist or model grants as production approval. `azure.yaml` names the same main file and group convention; this refactor validates Bicep offline, not a new `azd up` or cloud rollout.

For first deployment, `main.bicep` can create the registry with `deploymentTarget=foundation` before images exist. CI then builds/import-tests/scans/pushes images and invokes the same main file for `all` or one application. Application image builds are CI work, not a second Bicep composition.

## Optional and privileged profiles

All optional profiles are invoked in the **application** resource group:

```sh
az deployment group what-if -g rg-maf-dev-eus2-01 --parameters infra/main.model.dev.bicepparam
az deployment group what-if -g rg-maf-dev-eus2-01 --parameters infra/main.network.dev.bicepparam
az deployment group what-if -g rg-maf-dev-eus2-01 --parameters infra/main.memory.dev.bicepparam
az deployment group what-if -g rg-maf-dev-eus2-01 --parameters infra/main.access.dev.bicepparam
```

The model/Foundry role module explicitly targets `foundryResourceGroupName`; the operator needs deployment/resource permission there and at the root group. No new Foundry account is created. The network profile records the previously selected parallel foundation and dedicated registry data host, but the registry remains Basic as requested. Do not cut applications over until a reviewed Basic-compatible image delivery design and final network tests pass. Re-review network what-if after any refactor; historical foundation approval is not a new migration approval.

Every bootstrap role flag defaults false. Enable only the reviewed assignment set under a separate authorized operator: `bootstrapAcrPullRole`, `bootstrapMemoryRoles`, `bootstrapControlRoles`, `bootstrapSkillRole`, `bootstrapMonitoringRole` or `bootstrapFoundryRole`. `main.access.dev.bicepparam` selects the access target without implicitly enabling grants. Supply a real approved operator/agent object ID when its corresponding role requires one. Existing runtime and cleanup principals must exist for access-only bootstrap. Ordinary CI cannot use a disabled flag as proof that it has role-assignment permission.

The control containers module does not modify the existing preference account's version/soft-delete settings. The memory account profile deliberately retains the approved no-history dev policy; changing that policy needs separate deletion/restore review. Audit retention remains 30 days and Unlocked, and role GUID seeds are preserved.

## What cannot be one ordinary resource-group deployment

- **Its own target resource group:** the group must exist before a group-scoped deployment can run. A subscription-scoped parent could create it and call the patterns, but it needs subscription deployment/group-creation permissions. That is a possible alternative, not a technical prohibition; it would change the current dev permission boundary. The current workflow bootstraps a new stage/prod group explicitly, then uses this same root. [Azure deployment scopes](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/deploy-to-resource-group).
- **Entra directory provisioning and consent:** the existing provisioner uses Microsoft Graph for blueprint/agent objects and application roles. Subscription/resource-group RBAC does not grant directory authorization. Some Entra objects can be expressed with the Graph Bicep extension, but migrating that privileged flow is a separate reviewed change; it is not silently part of ordinary app CI. [Agent blueprint provisioning](https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/create-blueprint).
- **Secrets from external providers and artifact builds:** TMDB token issuance/rotation, user/admin consent and application image build/scan are inputs or pipeline operations. They are not plain ARM resource declarations.
- **Live policy/approval data:** stopped-policy initialization, policy recovery, unknown-outcome reconciliation and human approvals remain data-plane operator actions. An infrastructure redeploy must not seed over or clear authoritative accounting, approvals or kill state.

Everything in the active Azure resource composition is driven by the main file and its profiles. These exceptions concern scope, permission or non-resource lifecycle, not duplicate application compositions.

## Verification and migration record

```sh
python3 scripts/validate_infra.py
```

The validator compiles every resource module/pattern/fixture and parameter profile using synthetic values, verifies that the root is unique and resource modules contain no composition, compares authentication/private ingress/storage/retention/role contracts against pre-refactor compiled resources, and checks target isolation. It does not contact Azure Resource Manager or establish that a live what-if has zero changes.

`main.rg.bicep`, duplicate dev resource-group parameters and independent network/memory/model roots have been consolidated. Retired synthetic/network/Premium-registry experiments are retained under `fixtures/legacy/` for historical evidence only and are not called by ordinary environment deployment. The opt-in containment fixture remains reachable through the root for approved drills.

This cleanup requires a current Azure what-if before deployment, especially where nested deployment names/API versions changed. The managed-environment resource module retains the original working environment's API version; the parallel network pattern uses that shared module rather than a second environment implementation. Existing Azure resource addresses, auth/ingress settings, selected SKU and retention intent are preserved; compile/contract tests are not substitutes for hosted acceptance.
