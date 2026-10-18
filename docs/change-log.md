# Change log

This log records material implementation, deployment, authentication, and hosted-test changes. It intentionally excludes credentials, bearer tokens, prompt content, and other sensitive values.

## 2026-10-18 — Persistent CLI sign-in

- Changed `agent-chat` and the hosted acceptance script to share a named, encrypted OS-user-scoped Entra token cache plus a local non-secret account selector. Device-code sign-in is needed only when this state cannot silently refresh the user's authorization.
- The cache contains refresh credentials protected by the platform; the account selector is stored with user-only file permissions. Neither stores command-line or repository bearer tokens, and plaintext cache fallback remains disabled.
- Completed one device-code sign-in after the selector migration, then verified a separate process silently refreshed a Stage 1 API token without displaying a device code.

## 2026-10-18 — Restart acceptance

- Created an authenticated session on `ca-az-maf-stage1--0000008`, restarted that revision, and confirmed the next chat request returned `404`. This records the selected single-replica, in-memory session contract: restarts deliberately discard session state.

## 2026-10-17 — Foundry inference configuration

- Added the complete, non-secret `config/foundry-stage1.json` configuration for the existing `gpt-5` deployment in the `aif-homelab-rv6t99la` account. It uses the supported Chat Completions API surface, a 400,000-token model window, and the existing Stage 1 admission, time, token, and cost limits.
- Set the configuration's cost accounting to the published East US 2 Global Standard retail rates observed on 2026-10-17: $1.25 per million input tokens and $10.00 per million output tokens. These values reserve the configured maximum before each call and are not a replacement for Azure billing analysis.
- Made the Container App deployment template accept an explicit approved configuration path. It still defaults to deterministic offline mode until the live image and workload identity assignment are deployed.
- Re-pinned the Linux/amd64 Python 3.12.12 slim base image and uv build-tool image to their current manifests after their retired prior digests blocked the managed registry build.
- Corrected the image's virtual-environment build path so its executable entry points remain valid after the multi-stage image copy.
- Copied the application source into the runtime image and set its source path because the installed package uses an editable source reference during the bounded build.
- Assigned the Container App system identity the built-in `Cognitive Services OpenAI User` role at the existing Foundry account scope, then deployed image digest `sha256:731d2bac351d6f723f101e2fdb46ec0fa85e8d48986bf5c806f84b1d1767edcb` to live revision `ca-az-maf-stage1--0000004` with `AGENT_CONFIG=/app/config/foundry-stage1.json`. Both containers reached ready state with zero restarts.
- Updated the hosted acceptance script to reject deterministic offline replies while keeping model text out of the terminal output.

## 2026-10-17 — Foundry project access

- Assigned the Container App system identity the built-in `Foundry User` role at the `az-maf-agent-stage1` Foundry project scope.
- Retained its account-scoped `Cognitive Services OpenAI User` role because the selected `gpt-5` Chat Completions deployment is hosted on the parent Foundry account and requires that data-plane inference permission.

## 2026-10-17 — Live Foundry inference acceptance

- Completed the device-code-protected acceptance test against revision `ca-az-maf-stage1--0000004` after its managed-identity refresh.
- An approved user received non-offline model text for the first chat, second chat, and chat after reset. The test intentionally records only response lengths, not model text.
- Public unauthenticated session creation remained `401`; replaying an old revision remained `409`; the successful revision sequence was `1`, `2`, and `4`.
- Verified that a valid Azure management token, whose audience is not the Stage 1 API, is rejected with `401` at the public ingress.
- Added `--expect-forbidden` to the hosted acceptance script for a controlled allowed-user denial check. An initial device-code attempt timed out, then a valid approved-user token was acquired before the allowlist was temporarily replaced. The app returned `403`; the original allowlist was restored on healthy revision `ca-az-maf-stage1--0000008`.

## 2026-10-17 — Azure AI Foundry project

- Created the `az-maf-agent-stage1` project under the existing `aif-homelab-rv6t99la` Azure AI Services account in `rg-homelab-foundry`, East US 2.
- The project has a separate system-assigned identity and its own Foundry project endpoint.
- No model deployment, model-inference role assignment, or Container App inference configuration was added. The deployed Container App remains in deterministic fake-model mode.

## 2026-10-17 — Hosted Container App acceptance

- Corrected the API registration to request Entra v2 access tokens (`requestedAccessTokenVersion: 2`).
- Corrected the Container App and Easy Auth audience from the API identifier URI to the v2 access-token audience: API application ID `e7898571-069f-49c7-91b5-4b08a9edcb30`.
- Kept Easy Auth enabled with HTTPS required, `Return401`, no excluded paths, and the dedicated Stage 1 CLI application as the only allowed client.
- Added `scripts/test_container_app.py`, which uses device-code authentication without persisting or printing bearer tokens and verifies the public auth boundary plus session behavior.
- Verified a signed-in approved user can create a session, chat twice, receive stale-revision denial, reset, and chat again. The revision progression was 1, 2, and 4.

## 2026-10-16 to 2026-10-17 — Test foundation and deployment

- Created the dedicated East US 2 test resource group `rg-az-maf-stage1` with a Container Apps environment, Basic private registry, image-pull identity with `AcrPull`, and 30-day Log Analytics workspace.
- Built and pushed the non-root Linux/amd64 Stage 1 image to the private registry, pinned by digest in the deployment record.
- Deployed the fake-mode API with one replica, private-first ingress, Entra Easy Auth, and a separate system-assigned workload identity reserved for future model access.
- Enabled public HTTPS ingress only after confirming authentication settings. Verified no-token, invalid-token, and forged-header requests return 401; plain HTTP redirects to HTTPS.

## Repository commits

| Commit | Purpose |
| --- | --- |
| `391ffa0` | Hosted deployment templates, image build, and documentation |
| `a9ca3b3` | Hosted Container App acceptance script |
| `9d72074` | Dedicated-client validation in the test script |
| `303fea6` | Entra v2 API access-token configuration |
| `8c779d8` | Container App v2 audience alignment |
| `1a28709` | Hosted acceptance evidence |
