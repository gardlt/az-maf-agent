# Stage 1 hosted test runbook

**Retired on 2026-10-18:** The dedicated Azure resource group, Foundry project, and Entra app registrations were deleted. The endpoint and IDs below document the former test deployment and cannot be used as a current runbook without reprovisioning and updating configuration.

This runbook describes the former single-replica fake-model test deployment. It is not a production architecture and it has no durable session store.

## Former test deployment

The approved test foundation was in the SpaceColony subscription, resource group `rg-az-maf-stage1`, East US 2. A historical image was pinned to `azmafstage1mako261016.azurecr.io/az-maf-stage1@sha256:9aee3d497a5a46dd5169c698d0d92b8a2be7e35e1ab588ab21040645f14dfdfa`.

The former public test origin was `https://ca-az-maf-stage1.purplehill-879f4f4f.eastus2.azurecontainerapps.io`. It had one replica, HTTPS-only ingress, and Entra Easy Auth configured to return 401 for missing authentication. It must not be treated as a live endpoint.

## Build and deploy

Build the Linux image from the repository root, test it without network access, then push it to the approved private registry. Use the emitted digest, never a mutable tag, in the deployment parameter file. The external Docker Scout scan was intentionally skipped for this test.

```sh
docker build --platform linux/amd64 -t az-maf-stage1:local .
docker run --rm --network none --entrypoint python az-maf-stage1:local -c 'import os; assert os.getuid() == 10001'
```

Deploy [the foundation template](../deploy/foundation.bicep) first. It creates a Basic registry with admin access disabled, a pull-only managed identity, a Container Apps environment, and a 30-day Log Analytics workspace. Those resources are billable.

Use a private, mode-600 ARM parameters file outside the repository for [the app template](../deploy/container-app.bicep). It contains the app identifiers and the Easy Auth secret. Never supply the secret on a command line, in source control, or in a CLI prompt. Run `what-if` before creation:

```sh
az deployment group what-if --resource-group <TEST_RESOURCE_GROUP> \
  --template-file deploy/container-app.bicep \
  --parameters @/private/path/to/parameters.json \
  --result-format ResourceIdOnly
```

Initially keep `externalIngress` false. Verify the revision and the Easy Auth readback: enabled, `Return401`, no excluded paths, HTTPS required, exact access-token audience, and only the approved CLI client. Then set `externalIngress` to true and deploy the same reviewed template. Set the API registration redirect URI to `<public-origin>/.auth/login/aad/callback`.

Set the API registration's `requestedAccessTokenVersion` to `2`. The Container App and Python API validate v2 issuer and client claims; a legacy v1 access token will be rejected before it reaches the application.
For this v2 API, configure the Container App `audience` and Easy Auth allowed audience as the API application ID (`e7898571-069f-49c7-91b5-4b08a9edcb30`), not its `api://` identifier URI.

## Acceptance checks

Use an Entra access token obtained through the approved public CLI application. Do not record bearer tokens or prompt text. Check:

| Probe | Expected result |
| --- | --- |
| Missing token | 401 |
| Invalid or forged identity header | 401 |
| Authenticated caller outside allowlist or without `Chat.Access` | 403 |
| Allowed user creates, chats twice, resets, then chats | Fake context counts 1, 2, 1 |
| Replayed revision | 409 and unchanged history |
| Plain HTTP | Redirected to HTTPS |

The Python API independently verifies the original bearer token; it does not trust Easy Auth identity headers or accept an Easy Auth session cookie as identity. The system-assigned workload identity is reserved for a later, separately reviewed live-model configuration.
