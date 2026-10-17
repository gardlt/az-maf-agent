# Change log

This log records material implementation, deployment, authentication, and hosted-test changes. It intentionally excludes credentials, bearer tokens, prompt content, and other sensitive values.

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
