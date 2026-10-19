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

## Current dev registration IDs

These are identifiers, not credentials:

- API: `67b8f4b9-71e4-4815-b8b5-a0a4fd7bc0d7`
- CLI: `d8bd0dd5-388c-4436-a64b-bdfcdbeebe7f`
- Movie MCP: `f992b99b-25b8-4a99-8c00-7157b8edf4de`

The registrations still need their service principals and API scope/client consent configured before authenticated Container Apps deployment.
