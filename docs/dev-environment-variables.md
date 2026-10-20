# Dev environment variables

The local deployment uses `infra/main.dev.bicepparam`. Keep actual values in a user-only file such as `.env.dev` (ignored by Git) and load it into the shell before running Azure CLI commands. Never commit or paste secret values.

| Variable | Required | Purpose | Example or source |
| --- | --- | --- | --- |
| `AZURE_LOCATION` | yes | Azure region | `eastus2` |
| `MAF_REGISTRY_NAME` | yes | Globally unique ACR name | `crmafdev<unique>`; lowercase letters and numbers |
| `MAF_AGENT_IMAGE` | yes | Digest-pinned agent image | `<registry>.azurecr.io/az-maf-agent@sha256:<digest>` |
| `MAF_MCP_IMAGE` | yes | Digest-pinned movie MCP image | `<registry>.azurecr.io/az-maf-movie-mcp@sha256:<digest>` |
| `MAF_TENANT_ID` | yes | Microsoft Entra tenant | `az account show --query tenantId -o tsv` |
| `MAF_AGENT_AUDIENCE` | yes | Agent API app ID / audience | Dev API app registration ID |
| `MAF_ALLOWED_USERS` | yes | Comma-separated approved user object IDs | `az ad signed-in-user show --query id -o tsv` |
| `MAF_API_CLIENT_ID` | yes | Agent API app registration client ID | Same dev API app ID |
| `MAF_CLI_CLIENT_ID` | yes | Public CLI client app ID | Dev CLI app registration ID |
| `MAF_AUTH_CLIENT_SECRET` | secret | Easy Auth registration secret | Generate once for the dev API app; store only in `.env.dev` |
| `MAF_MCP_AUDIENCE` | yes | Movie MCP API app ID / audience | Dev MCP app registration ID |
| `TMDB_API_READ_ACCESS_TOKEN` | secret | TMDB read-only bearer token | Read from the rotated local secret file; do not commit |

The subscription and resource names are fixed by `infra/main.dev.bicepparam` and the current Azure account. The deployment also needs Docker locally to build the two images and `az acr login` to push them after the registry exists.

## Load and deploy from the CLI

The parameter file reads the process environment. Load the local file, then run the subscription deployment:

```sh
set -a
. ./.env.dev
set +a
az deployment sub what-if \
  --name maf-dev \
  --location "$AZURE_LOCATION" \
  --subscription "$(az account show --query id -o tsv)" \
  --template-file infra/main.bicep \
  --parameters infra/main.dev.bicepparam
```

After reviewing the what-if, replace `what-if` with `create`. The `.env.dev` file is ignored by Git and must remain user-only.

The same values can be stored in an `azd` environment instead of a shell file:

```sh
azd env new maf-dev
azd env set AZURE_LOCATION eastus2
azd env set MAF_REGISTRY_NAME crmafdev<unique>
azd env set MAF_TENANT_ID "$(az account show --query tenantId -o tsv)"
azd env set MAF_ALLOWED_USERS "$(az ad signed-in-user show --query id -o tsv)"
```

Use `azd env set` for identifiers and image references. Set secrets from a protected shell or secret store; do not put them in a committed `.bicepparam` file.

## Configure GitHub Actions from the CLI

GitHub environment variables and secrets can be populated without putting values in workflow YAML. Run these from a shell where `.env.dev` is loaded:

```sh
gh variable set AZURE_LOCATION --env dev --body "$AZURE_LOCATION"
gh variable set MAF_REGISTRY_NAME --env dev --body "$MAF_REGISTRY_NAME"
gh variable set MAF_TENANT_ID --env dev --body "$MAF_TENANT_ID"
gh variable set MAF_AGENT_AUDIENCE --env dev --body "$MAF_AGENT_AUDIENCE"
gh variable set MAF_ALLOWED_USERS --env dev --body "$MAF_ALLOWED_USERS"
gh variable set MAF_API_CLIENT_ID --env dev --body "$MAF_API_CLIENT_ID"
gh variable set MAF_CLI_CLIENT_ID --env dev --body "$MAF_CLI_CLIENT_ID"
gh variable set MAF_MCP_AUDIENCE --env dev --body "$MAF_MCP_AUDIENCE"
gh secret set AZURE_CLIENT_ID --env dev < ./azure-deploy-client-id.txt
gh secret set AZURE_TENANT_ID --env dev < ./azure-tenant-id.txt
gh secret set AZURE_SUBSCRIPTION_ID --env dev < ./azure-subscription-id.txt
gh secret set MAF_AUTH_CLIENT_SECRET --env dev < ./maf-auth-client-secret.txt
gh secret set TMDB_API_READ_ACCESS_TOKEN --env dev < ./.tdb-token
```

The three Azure deployment identity files must contain the values for the federated deployment application. Keep all five files outside Git and delete temporary copies after setting the secrets. The deployment application's federated credential subject must be `repo:gardlt/az-maf-agent:environment:dev`.

## Current dev registration IDs

These are identifiers, not credentials:

- API: `67b8f4b9-71e4-4815-b8b5-a0a4fd7bc0d7`
- CLI: `d8bd0dd5-388c-4436-a64b-bdfcdbeebe7f`
- Movie MCP: `f992b99b-25b8-4a99-8c00-7157b8edf4de`

The dev registrations have configured service principals and consent; authenticated hosted acceptance succeeds.


## Stage 4 memory settings

No additional GitHub secret is needed. Bicep supplies these non-secret container
settings; storage authentication uses each workload's managed identity.

| Setting | Dev value |
| --- | --- |
| `ENABLE_MEMORY` | `true` (agent only) |
| `MEMORY_BACKEND` | `azure_blob` (agent only) |
| `MEMORY_ACCOUNT` | `stmafmemdevmako261019` |
| `MEMORY_CONTAINER` | `preferences` |
| `MEMORY_POLICY` | `/app/config/memory-policy.json` |
| `MEMORY_ALLOWED_USERS` | Approved `MAF_ALLOWED_USERS` subset (agent only) |

`infra/main.dev.bicepparam` also pins cleanup job and portal alert names. Operator
bootstrap grants agent/job system identities container-scoped Blob Data Contributor.
Ordinary CI leaves `bootstrapMemoryRoles=false` and cannot grant roles. See the
[Stage 4 guide](stages/stage-4/stage-4-memory.md) for lifecycle policy, tests, and operations.
