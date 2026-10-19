## 2026-10-19 — Stage 4 runtime and dev rollout

- Added bounded asynchronous memory access, cancellation fencing before writes, worker admission limits, and explicit ambiguous-write reconciliation without retries.
- Added user-scoped minimal recall as untrusted model context, shared operation/token budgets, final freshness checks, and history invalidation on generation changes.
- Added hourly conditional expiry cleanup with a dedicated job identity, pinned namespace, page/time bounds, and retained empty generation fences.
- Added CLI inspect/save/correct/forget commands and reproducible memory storage, cleanup job, role bootstrap, and dev deployment settings.
- Local validation: 121 tests pass, Ruff passes, and both Bicep entry points compile. Dev storage has been provisioned; hosted acceptance is pending this rollout.

## 2026-10-19 — Stage 4 hosted configuration groundwork

- Added operator-only Blob memory startup configuration with explicit Entra tenant/user permissions, approved backend, user scope, and 30-day retention checks.
- Added disabled-by-default memory settings to the Container App module. No cloud resources or memory roles were changed.
- Verified 113 tests, Ruff checks, and Container App Bicep compilation. Async access, scheduled cleanup, model recall, and hosted acceptance remain open.

# Change log

This log records material implementation, deployment, authentication, and hosted-test changes. It intentionally excludes credentials, bearer tokens, prompt content, and other sensitive values.

## 2026-10-19 — Stage 4 Blob adapter and dev policy

- The user selected one Blob document per user and approved no dev backups/version history, immediate expiry/deletion exclusion, and expired-record cleanup within 24 hours.
- Implemented a managed-identity Blob adapter with pinned destinations, validated bounded documents, conditional creation/ETag updates, and persistent empty generation records after forgetting. Extracted the shared state transition engine from the RAM fixture; durable services require an explicit audit callback.
- Added Blob fixture tests for scope/corruption, conditional conflicts, adapter recreation, expiry, and ambiguous commits; the suite passes 106 tests. Prepared and compiled the private-container storage module and explicit dev parameters. Hosted memory and the scheduled cleanup worker are not enabled yet.

## 2026-10-19 — Stage 4 memory groundwork

- Recorded the user's policy choice: explicitly saved movie genre/language preferences follow the same user across sessions and expire after 30 days. The cloud storage product is still undecided.
- Added typed preference/provenance contracts, owner/purpose-scoped storage operations, consent/category checks, optimistic generations/revisions, inspect/correct/forget APIs, and session operation budgets. The API is disabled by default; only an injected RAM fixture is implemented.
- The 95-test local suite covers consent before effects, cross-scope access, expiry, deletion races, concurrent creates, forged API scope, skill-origin denial, and ordinary chat never granting durable consent. No cloud memory resource or model recall path was enabled. See [the Stage 4 checkpoint](stage-4-memory.md).

## 2026-10-19 — Stage 3 approved Markdown skills

- Implemented the user-selected movie research and movie-night skills, a reviewed digest-pinned registry, immutable bounded loader, permission intersection, and CLI/API selection. Updated CI/deployment triggers for skill bundles.
- Added bounded read-only Azure tag control gates and separate operator disable/enable/revoke commands. Dev reuses its existing resource group and Foundry model; the app has Reader for control metadata and Foundry User for inference. No new Azure resource was created.
- All 81 local tests pass, including injection, no-write effects, path/integrity, retry/final-response revocation, immutable content, budget, cancellation/reset, and control failure cases. Hosted skills each returned 200 with one MCP read and an exact manifest digest. Actual workload write proposals were denied downstream and the movie record stayed unchanged.
- Live disable returned 409 within 1.3 seconds after the operator update and preserved the ready revision; the approved skill was restored. Stage 4 memory case 4 and Stage 5 production shared controls remain explicitly separate. See [Stage 3 validation](stage-3-validation.md).

## 2026-10-18 — Reproducible Azure infrastructure layout

- Renamed `deploy/` to `infra/` and added the Azure Developer CLI-style `azure.yaml` entrypoint with `infra/main.bicep` as the subscription-scoped composition root.
- Moved reusable and test-specific Bicep templates under `infra/modules/`. Added environment-specific `main.dev.bicepparam` and `main.stage.bicepparam` files plus an azd-compatible environment-driven `main.bicepparam`. Secrets and deployment-specific identity values are read from environment variables and are not committed.
- The composition root provisions the resource group, shared Container Apps foundation, agent, and private FastMCP app together, wiring the agent managed identity into the MCP authorization boundary.

## 2026-10-18 — Dedicated Stage 1/2 Azure teardown

- At the user's direction, removed the dedicated `rg-az-maf-stage1` test foundation and both hosted apps (`ca-az-maf-stage1` and `ca-az-maf-movie-mcp`), including their Container Apps environment, registry, Log Analytics workspace, and image-pull identity. The separate short-lived Stage 2 network-test resources had already been removed.
- Removed the dedicated `az-maf-agent-stage1` Foundry project under `aif-homelab-rv6t99la`, the three dedicated Entra app registrations and matching service principals (`az-maf-stage1-api`, `az-maf-stage1-cli`, `az-maf-movie-catalog-stage2`), and the agent's external Foundry account/project and movie-catalog app-role grants. The shared Foundry account, its existing model deployment, and the unrelated `hermes-agent` project were preserved.
- The hosted URLs and cached tokens for the removed app registrations are no longer usable. The repository, local fake-mode app, local FastMCP implementation, and user-owned TMDB token file remain. Earlier hosted validation entries below are historical results, not current availability claims.

## 2026-10-18 — Stage 2 controlled-egress acceptance

- The user approved a short-lived separate Consumption workload-profile test environment and cleanup. Foundation what-if predicted four new resources; app what-if predicted two new Container Apps; neither predicted changes to the working Stage 1 apps. Deployed `stage2-egress-foundation-20261018` and `stage2-egress-apps-20261018` with an NSG rule for the test-owned Stage 1 public IP `20.14.237.110/32`.
- Duplicate agent revision `ca-az-maf-agent-nettest--imlae64` and private MCP revision `ca-az-maf-mcp-nettest--5m66ed5` were healthy on digest-pinned images. The duplicate agent received temporary Foundry account/project roles and only the catalog API's `Catalog.Read` app role. Signed-in movie read and live Foundry chat/reset checks passed with the NSG deny active. Missing and wrong-audience tokens, forged headers, and write proposals failed; the private MCP was not publicly reachable.
- From the same agent replica, a direct HTTPS request to the test-owned destination returned `401` while the NSG rule was temporarily Allow. After switching that rule to Deny, a fresh direct connection timed out in 8.1 seconds; a direct TMDB control request still returned `401` in 0.3 seconds. This proves the selected one-destination network test, not a general outbound allowlist. The existing Log Analytics workspace recorded 28 agent and 29 MCP system events. [Validation](stage-2-validation.md) records the exact rule and scope.
- Rebuilt and deployed the working agent from the pushed source with `.tdb-token` excluded from the Azure source archive. Revision `ca-az-maf-stage1--0000013`, digest `sha256:dd7c5bfd78a079538050cad3da83466cce82427869da1e9a5d0d90d1b47180f5`, passed the signed-in movie read and hosted Credits checks.
- Removed the temporary `Catalog.Read` app-role assignment, both Foundry role assignments, both duplicate Container Apps, the test environment, VNet/subnet, and NSG. Azure resource listing showed no `nettest` resources in `rg-az-maf-stage1`, and the Azure-managed backing resource group no longer existed. The original hosted agent and MCP passed a signed-in movie read after cleanup.

## 2026-10-18 — Hosted credits, TMDB token rotation, and network-test preparation

- Added an authenticated `/about` page on agent revision `ca-az-maf-stage1--0000012` (digest `sha256:24f6ca06d1c9bd6f21dff0fc22b2ea5b42b452146d5dd1c0503ae9f9be7daa49`). Hosted unauthenticated access returned `401`; an approved user received `200` with TMDB's required notice and approved logo. The CLI now points movie users to the Credits page.
- Found that `.tdb-token` was ignored by Git but not by the Azure image-build source archive. Previous build uploads may therefore have contained the old token, although the Dockerfiles did not copy it into either image. Added `.tdb-token` to `.dockerignore` and verified Azure CLI's source packer excludes it. The user rotated the TMDB token and replaced the private local file; deployment `stage2-tmdb-token-rotation-20261018` updated the Container App secret, its revision was restarted, and a signed-in hosted `get_movie(tmdb_11)` returned *Star Wars*. The transient deployment parameter file was removed.
- Prepared a separate Consumption workload-profile network-test environment and two digest-pinned test-app definitions. A foundation what-if predicted four new resources and no existing-resource changes. Both Bicep templates compile. The foundation and duplicate apps have **not** been deployed; the network-rule deny test remains open.
- The locked local suite passed 47 tests, and lint, formatting, and whitespace checks passed.

## 2026-10-18 — TMDB replaces synthetic catalog

- After the initial code commit, the user supplied a local TMDB token file path. Its permissions were restricted to `0600` and it was added to `.gitignore`. A live search returned three *Star Wars* records; `tmdb_11` details returned *Star Wars* with `source: TMDB`. A local `agent-chat --movies` FastMCP stdio smoke test confirmed the movie title, TMDB rating label, and attribution notice. The token value was not printed or committed.
- Azure what-if predicted only the private MCP Container App would change. Deployment `stage2-tmdb-mcp-20261018` succeeded with the TMDB credential as a secure Container App secret. MCP revision `ca-az-maf-movie-mcp--0000002` and agent revision `ca-az-maf-stage1--0000011` became healthy on the digest-pinned images listed below. Both older synthetic MCP revisions are inactive.
- Signed-in hosted checks passed: details and search `200`; unauthenticated read `401`; invalid ID and limit `422`; unknown write tool `403`; empty search and missing valid ID handled correctly. From inside the new agent revision, a tokenless MCP request and a signed wrong-audience managed-identity request both returned `401`; the internal MCP hostname returned `404` from outside the environment. A Foundry model-selected read completed with one MCP call and chat `200`. The Stage 1 live chat/reset regression also passed on the new agent revision without a new device-code prompt.
- Controlled-egress enforcement remains open. The existing environment still has no VNet or workload profiles. A hosted Credits page was deployed later, as recorded above.
- The user selected TMDB as the sole movie source. The repository now uses a pinned, read-only TMDB search/details adapter behind the two FastMCP tools and agent-side `tmdb_<id>` validation. The synthetic catalog fixture and admin PUT source were removed from the target design. Existing hosted synthetic results remain historical evidence, not TMDB acceptance.
- The temporary `ca-az-maf-catalog-admin-probe` Container App was deleted. Its only `Catalog.Admin` app-role assignment and its user-assigned managed identity were also removed. The unassigned `Catalog.Admin` role definition remains on the catalog API registration until reviewed removal.
- The TMDB token is not stored in the repository. It was read from a private local file for live validation and securely supplied to the Container App; the transient deployment parameter file was deleted after deployment.
- The user confirmed non-commercial teaching use. Added a repository [Credits](credits.md) page with TMDB's approved primary logo and required notice. The CLI shows the notice in movie mode; a separate hosted user interface will need to show the credits as well.
- The locked local suite passed 46 tests, and lint and whitespace checks passed. Built private ACR images for the TMDB MCP (`sha256:8f0b79e3bf22f576acd4b3bfcf5be17d40bcbdb55522081905bd6c55a802890f`) and matching agent (`sha256:4fe10a9dc7f8d19865987acd6da2d8ab66ab1dcedce2ea422fdebf6f6f6274bf`).

## 2026-10-18 — Hosted catalog admin PUT

- Added [Stage 2 architecture](stage-2-architecture.md) and [network design](stage-2-network-design.md) records covering service topology, trust boundaries, read/write flows, deployment identities, network limits, and the remaining hosted acceptance plan. The network design is a proposal; it does not authorize or deploy a new foundation.
- Mounted a separately authenticated FastAPI admin PUT route beside the two FastMCP read tools, with a shared in-memory catalog. The route requires a signed Entra v2 token for the catalog API, the configured tenant and admin object ID, and the `Catalog.Admin` application role. Local invalid-token, reader-denial, and read-after-write tests passed; the full suite reached 54 tests.
- Added `Catalog.Admin` to the existing catalog API registration and assigned it to dedicated admin test identity `id-az-maf-catalog-admin-test`. Deployed catalog image digest `sha256:209edec91beb1da58fd028601f7ea5a3a576c7f8d270f2d41f5963258c2b771d` as healthy revision `ca-az-maf-movie-mcp--0000001` with internal ingress.
- Deployed temporary ingress-free `ca-az-maf-catalog-admin-probe` and used its admin managed identity to replace synthetic record `movie_000101`. The direct downstream PUT returned `200` and catalog revision `1`. The temporary title is *Brass Comet Admin Test*; it must be restored to *Brass Comet* after read verification.
- The hosted explicit agent read regression passed after rollout. The follow-up read of the modified record, direct downstream PUT denial for the actual agent identity, record restoration, and probe cleanup remain pending. Automatic approval review rejected the follow-up command due to an account usage limit before execution. Stage 2 remains open, including controlled-egress evidence.
- Hardened the MCP reader to require a list-valued `roles` claim and added regression coverage. This change was made after the current hosted image build; it will require a new image rollout.

## 2026-10-18 — Model-selected Stage 2 reads

- Added an opt-in, application-owned model tool loop that advertises only the two pinned read functions, validates proposed calls and results, limits a run to two sequential MCP read attempts, and charges model calls/retries to the existing budget ledger. Session history retains only the final text pair. Local tests cover forbidden calls, duplicate arguments, loop limits, injected tool text, and reset cancellation.
- Deployed agent image digest `sha256:809c1982ff0e342e290274a786f92716eb9f46be1bf3a98fe2138fcc568bb211` as revision `ca-az-maf-stage1--0000010` with `ENABLE_MOVIE_MODEL_TOOLS=true`.
- Verified a signed-in live model response after exactly one MCP read of `movie_000103`. The Stage 1 live-chat acceptance and explicit movie-read/denial checks also passed after rollout. The complete local suite passed 51 tests.
- Deployed admin PUT authorization and controlled-egress network checks remain open; Stage 2 is not accepted yet.

## 2026-10-18 — Hosted Stage 2 MCP read path

- Deployed `ca-az-maf-movie-mcp` as an internal second app in the existing Stage 1 Container Apps environment. Its image digest is `sha256:dd2db134a9031138fc65c24e96c921078944e0fcdabf0ecff98d8e0133996b77`; the app has its own system-assigned identity.
- Registered a separate Entra v2 MCP API (`ddf8d97d-9b4a-4ce8-9fd2-a7293ad909cb`) with only the `Catalog.Read` application role and assigned it to the existing agent system identity. The MCP verifies issuer, audience, signature, tenant, agent object ID, and role; the agent obtains a managed-identity token for this audience.
- Updated the existing agent to image digest `sha256:349926fdc0ddc20e226bb0df36eaed86315b1b7067e55f88db16be8b23ff2b85` and configured its private MCP endpoint. Revision `ca-az-maf-stage1--0000009` became healthy at 100% traffic.
- Added `scripts/test_movie_container_app.py`. The signed-in hosted exercise recorded session creation `200`, unauthenticated movie read `401`, managed-identity-backed MCP read `200`, and denied write proposal `403`. The internal MCP hostname returned `404` from outside the environment and `401` for a no-token request from inside the agent container.
- Re-ran the Stage 1 hosted acceptance on the new revision: unauthenticated create `401`; approved create, two live-model chats, reset, and chat after reset `200`; stale replay `409`; revision sequence `1`, `2`, `4`.
- The current environment has no VNet or workload profiles; outbound destination blocking and the other specified deployed network exercises are not yet evidenced. Model-selected tool calls and deployed admin PUT authorization also remain open.

## 2026-10-18 — Stage 2 local catalog foundation

- Added the agent-side pinned FastMCP client and explicit `/search` and `/movie` CLI commands, with an opt-in authenticated API route. Local reads are session scoped, bounded, revocable, and validated on both sides of the protocol.
- Converted the repository to a uv workspace monorepo: `apps/agent` owns the CLI/chat API and `apps/movie-catalog-mcp` owns catalog contracts, data, and its HTTP adapter. The catalog package now owns its workload-identity and denial contracts, so it no longer imports agent implementation types.
- Replaced the planned catalog transport with a FastMCP 4 server. Its registry exposes only `search_movies` and `get_movie`; the admin-only PUT adapter is a separate HTTP surface and cannot be discovered or invoked through MCP.
- Added the bundled, versioned `synthetic-movies-v1` fixture of invented movie records and verified it is included in the distributable wheel.
- Added the pinned local dispatcher for only `search_movies` and `get_movie`, including strict schemas, deterministic ordering, a bounded not-found result, output revalidation, a serialized-result cap, explicit reader permissions, and current-tool revocation.
- Added local contract tests for valid reads, invalid/extra arguments, unknown tools, unauthorized callers, revocation, and malformed catalog records. This does not add model tool registration, an MCP transport, deployed service identities, or deployed network acceptance.
- Added the local `PUT /movies/{catalog_id}` adapter and separate catalog-admin contract. It accepts complete, schema-valid replacement records only when the path/body IDs match an existing record. Direct agent-identity PUT receives `403` and preserves catalog revision/state; deployment authentication and ingress are intentionally not configured yet.

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
