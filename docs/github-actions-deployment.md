# GitHub Actions deployment

The repository has `CI`, `Infra` and `Deploy Azure environment` workflows. CI runs the application suite and lint/format checks. Infra runs `scripts/validate_infra.py` to compile resource modules, patterns, fixtures and parameter profiles and verify resource/security contracts and target isolation with synthetic values.

## One infrastructure entry point

All deployment steps use `infra/main.bicep` or a `main.<environment>.bicepparam` profile bound to it. `infra/modules/` contains resource-level modules; `infra/patterns/` composes the agent application, movie MCP and shared resources. See the [infrastructure guide](../infra/README.md) for targets, scope, bootstrap exceptions and migration details.

The deployment workflow first invokes the root with `deploymentTarget=foundation` to ensure the registry/environment exist. It builds the selected non-root image(s), runs import smoke tests and local SBOM/High-Critical scanning, pushes digest-pinned images, previews the selected graph, and invokes the same root in incremental mode.

Main changes matching deployment paths automatically deploy `all` to **dev**. Manual runs select `dev`, `stage` or `prod` and `agent`, `movie-mcp` or `all`. A targeted `agent` invocation reconciles the agent pattern, including its enabled cleanup job/health rule; a targeted `movie-mcp` invocation reconciles only the MCP pattern. They resolve existing shared resources and do not redeploy the other service. Shared infrastructure/configuration changes use `all`.

A single entry point does not mean one invocation before artifacts exist: registry bootstrap precedes build/push, then application provisioning uses the same file with a different target. All resource deployments use incremental mode. Do not use complete mode with target subsets.

## Permissions and promotion

The root is resource-group scoped. Dev uses its existing resource group and does not gain subscription deployment or role-write authority from this refactor. For a selected new stage/prod environment, the workflow explicitly creates/selects the target group with `az group create`, then invokes the same group-scoped main. Its deployment identity must have that separately approved group-creation permission. No normal main merge selects stage/prod.

Require actual environment reviewers/branch restrictions for higher environments and required CI/Infra checks in branch protection. YAML references to environments do not establish that those protections are configured. The current `azure.yaml` points at the same main and group naming convention; offline compilation is not proof of a successful `azd up`.

Azure login uses GitHub OIDC. Restrict federation to this repository and matching environment subject, for example `repo:gardlt/az-maf-agent:environment:dev`. Deployment identity, runtime identity, Agent ID and operator identity are different authorities. All bootstrap role flags default false; ordinary CI does not grant roles. An operator separately provisions pull/storage/control/monitoring/Foundry/skill roles and the Entra directory objects. A fresh environment is not ready merely because its ARM resources exist: scoped grants, required policy/control initialization, secrets and hosted acceptance remain prerequisites.

## Environment settings

Supply the reviewed per-environment variables `AZURE_LOCATION`, `MAF_REGISTRY_NAME`, `MAF_REGISTRY_SKU`, `MAF_TENANT_ID`, `MAF_AGENT_AUDIENCE`, `MAF_ALLOWED_USERS`, `MAF_API_CLIENT_ID`, `MAF_CLI_CLIENT_ID` and `MAF_MCP_AUDIENCE`. Agent ID/tracing additionally use the explicit enable flags and blueprint/agent identifiers recorded in the [environment inventory](dev-environment-variables.md). The dev profile retains memory, guardrails and approved skills; stage/prod configuration and identities require their own acceptance.

Environment secrets include `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `MAF_AUTH_CLIENT_SECRET` and `TMDB_API_READ_ACCESS_TOKEN`. Client/tenant/subscription identifiers are non-secret values even if stored in GitHub's secret namespace. There is no Azure deployment client secret: OIDC provides Azure authentication. The API authentication secret and TMDB token remain secret inputs; never commit or echo them.

The workflow supplies `MAF_AGENT_IMAGE` and/or `MAF_MCP_IMAGE` after the selected scan/push. Empty unselected image parameters are permitted for a targeted run; a selected service requires its digest-pinned image. Local full deployment requires both image variables and all matching auth/secret settings.

```sh
az deployment group what-if \
  --resource-group rg-maf-stage-eus2-01 \
  --parameters infra/main.stage.bicepparam
```

Network/model/access/drill targets are explicit operator profiles through the same root, not ordinary workflow side effects. This cleanup does not authorize app network cutover, registry SKU upgrade, broader directory permissions or policy/accounting reset.
