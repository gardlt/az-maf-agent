# GitHub Actions deployment

The repository has three workflows:

- `CI` runs application tests, lint, formatting, and dependency checks.
- `Infra` compiles every Bicep module and validates all parameter-file syntax with non-secret placeholder values.
- `Deploy Azure environment` provisions the selected environment foundation, then targets `agent`, `movie-mcp`, or `all`. A targeted run builds and updates only that Container App image. An `all` run builds both images, runs an Azure what-if, and deploys `infra/main.<environment>.bicepparam`.

The `main` branch deploys the full environment to the GitHub `dev` environment. A manual run can select `dev` or `stage` and update only the agent, only the movie MCP, or both. Configure approval rules on the `stage` GitHub environment before using it for release validation. Require both the `CI` and `Infra` checks in branch protection before allowing changes to `main`. The workflows use Azure workload identity federation through `azure/login`; no Azure client secret is stored in GitHub.

Run `all` once to bootstrap an environment. After that, a targeted `agent` or `movie-mcp` run builds, pushes, and rolls out only the selected image with `az containerapp update`; it does not redeploy the other service. Changes to shared infrastructure, identity, ingress, secrets, or environment configuration should use `all` so the composed Bicep deployment reconciles both services.

Configure one federated Azure application per deployment environment, or use one tightly scoped deployment identity with separate federated credentials. Each identity needs permission to create/update the environment resource group, assign the image-pull role in that group, push to its registry, and deploy the Container Apps resources. The federated credential subject should be restricted to this repository and the matching GitHub environment, for example `repo:gardlt/az-maf-agent:environment:dev` or `repo:gardlt/az-maf-agent:environment:stage`.

Create GitHub environment variables for both `dev` and `stage`:

`AZURE_LOCATION`, `MAF_REGISTRY_NAME`, `MAF_TENANT_ID`, `MAF_AGENT_AUDIENCE`, `MAF_ALLOWED_USERS`, `MAF_API_CLIENT_ID`, `MAF_CLI_CLIENT_ID`, and `MAF_MCP_AUDIENCE`.

Create GitHub environment secrets:

`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `MAF_AUTH_CLIENT_SECRET`, and `TMDB_API_READ_ACCESS_TOKEN`.

The registry name must be globally unique and contain only lowercase letters and numbers. The API, CLI, and MCP application registrations referenced by each environment must already exist, and their audiences must match the values supplied to that environment. Rotate the TMDB token through TMDB and replace the GitHub environment secret when it changes; never paste it into workflow files or parameters.

For local deployment, export the same variables and run:

```sh
az deployment sub what-if \
  --location "$AZURE_LOCATION" \
  --parameters infra/main.stage.bicepparam
```

The deployment workflow intentionally performs the foundation deployment before the image push because the registry is created by that foundation. The final deployment then supplies the pushed image digests through the process environment consumed by the `.bicepparam` file.
