# Stage 2 validation — TMDB movie MCP

## Current TMDB validation — 2026-10-18

The user selected TMDB as the sole movie source and confirmed non-commercial teaching use. The locked local suite passed 46 tests; Ruff lint/format and whitespace checks passed. With the API Read Access Token in a private local file, a live adapter check returned three *Star Wars* search records and `get_movie(tmdb_11)` returned *Star Wars*, with `source: TMDB`. A local `agent-chat --movies` smoke test used FastMCP stdio for `/search Star Wars` and `/movie tmdb_11`; the CLI displayed the title, TMDB rating label, and attribution notice and exited successfully. The token value was neither printed nor committed. [Credits](credits.md) includes TMDB's approved logo and notice.

The Azure what-if showed only `ca-az-maf-movie-mcp` changing. Deployment `stage2-tmdb-mcp-20261018` succeeded; revision `ca-az-maf-movie-mcp--0000002` is healthy on digest `sha256:8f0b79e3bf22f576acd4b3bfcf5be17d40bcbdb55522081905bd6c55a802890f` and references a Container App secret for the TMDB token. The matching agent revision `ca-az-maf-stage1--0000011` is healthy on digest `sha256:4fe10a9dc7f8d19865987acd6da2d8ab66ab1dcedce2ea422fdebf6f6f6274bf`. Both older synthetic MCP revisions are inactive. The temporary synthetic admin probe, role assignment, and identity were removed.

The signed-in hosted checks recorded session creation `200`, unauthenticated movie read `401`, `get_movie(tmdb_11)` `200` with title *Star Wars*, and unknown write tool `403`. Hosted search returned `200` with TMDB-labeled records; malformed ID and limit 11 returned `422`; a no-match search returned an empty `200`; and a missing valid ID returned `not_found: true` with `200`. The Foundry model selected one MCP read and completed chat with `200`. The Stage 1 hosted regression passed: unauthenticated create `401`; approved create, two live chats, reset, and post-reset chat `200`; stale replay `409`; revisions `1`, `2`, `4`. The encrypted CLI auth cache supplied the token without another device prompt.

The MCP is still internal to the existing Container Apps environment. On the new agent revision, an internal MCP request without a token returned `401`; a signed managed-identity token for the Foundry audience also returned `401`. A request to the MCP's internal hostname from outside the environment returned `404`. The remaining Stage 2 gaps are a hosted user-interface Credits surface and deployed controlled-egress rules/tests. The environment has no VNet or workload profiles, so Azure's documented UDR firewall pattern cannot be applied to it as it stands. See [TMDB integration](tmdb-integration.md), [network design](stage-2-network-design.md), and [the revised Stage 2 task](tasks/stage-2-movie-mcp.md).

## Historical synthetic validation

The evidence below predates the TMDB rollout. It describes the old synthetic catalog and admin PUT experiment and does not count as TMDB acceptance.

The deployed components and trust boundaries are described in [Stage 2 architecture](stage-2-architecture.md).

On 2026-10-18, the agent called the separate `movie-catalog-mcp` package through FastMCP's stdio protocol. The agent accepts only the pinned `search_movies` and `get_movie` schemas, validates arguments before connecting, and revalidates the returned synthetic catalog record within an 8 KiB bound. Direct `put_movie` proposals are denied before dispatch. Revoking `get_movie` denies subsequent calls. The catalog's separate admin PUT contract remains outside MCP; local tests verify a reader identity cannot mutate its state.

Run the local exercise from the repository root:

```sh
uv sync --locked --all-packages
uv run --locked agent-chat --movies
```

In the CLI, enter `/search lantern`, `/movie movie_000103`, and `/quit`. The displayed rating is synthetic. The completed smoke test found *The Last Lantern* through both read operations. The test suite and lint commands are `uv run --locked pytest -q`, `uv run --locked ruff check apps`, and `uv run --locked ruff format --check apps`.

On 2026-10-18, a fresh local CLI smoke run used `/search lantern`, `/movie movie_000103`, `hello`, `/reset`, and `/quit`. Both FastMCP reads returned *The Last Lantern*; the offline chat completed and reset succeeded. The full local suite passed 54 tests. This is local behavior, not a new hosted inference result.

The separate MCP app `ca-az-maf-movie-mcp` now runs with internal ingress in the existing `cae-az-maf-stage1` environment. It uses its own system-assigned identity and accepts Entra v2 tokens for application ID `ddf8d97d-9b4a-4ce8-9fd2-a7293ad909cb`. The agent identity `71edeec2-8419-4709-9120-35b3f8f86067` has the `Catalog.Read` application role. The MCP verifies the token signature, issuer, audience, tenant, agent object ID, and role. The agent uses its managed identity for the MCP token and sends no user token downstream. The MCP image is pinned to digest `sha256:dd2db134a9031138fc65c24e96c921078944e0fcdabf0ecff98d8e0133996b77`; the agent image is pinned to `sha256:349926fdc0ddc20e226bb0df36eaed86315b1b7067e55f88db16be8b23ff2b85`.

On 2026-10-18, the hosted test against agent revision `ca-az-maf-stage1--0000009` recorded authenticated session creation `200`, unauthenticated movie read `401`, authenticated `get_movie(movie_000103)` `200`, and a `put_movie` proposal `403`. The returned record was *The Last Lantern* and its rating was explicitly labeled synthetic. A request to the internal MCP FQDN from outside the environment returned `404`. A direct request from inside the agent container to that MCP FQDN without a token returned `401`. Run the test with `uv run --locked python scripts/test_movie_container_app.py`; it uses the existing encrypted CLI token cache when available and never prints the token.

The live Container Apps environment has no VNet configuration or workload profiles. It cannot provide user-defined-route egress evidence in this form. [Azure's documented UDR support](https://learn.microsoft.com/en-us/azure/container-apps/use-azure-firewall) requires a workload profiles environment. Controlled outbound destination blocking and the remaining deployed network exercises therefore require a separately reviewed network foundation. The private MCP read path is hosted and proven; full Stage 2 network acceptance is not.

The agent now has an opt-in application-owned model tool loop. It advertises only the pinned `search_movies` and `get_movie` schemas to the configured Foundry model, validates each proposed call before dispatch, permits at most two sequential read attempts per run, charges each model attempt to the existing ledger, and stores only the final user/assistant text pair in session history. Tool results remain untrusted data, and the MCP reader permission is checked again at dispatch. It is enabled on the hosted agent by `ENABLE_MOVIE_MODEL_TOOLS=true`; the original text-only path remains available when disabled.

On 2026-10-18, agent revision `ca-az-maf-stage1--0000010` became ready with image digest `sha256:809c1982ff0e342e290274a786f92716eb9f46be1bf3a98fe2138fcc568bb211`. The signed-in `scripts/test_movie_model_tools.py` run recorded session creation `200`, live chat `200`, and exactly one completed MCP read for `movie_000103`. It printed only the answer length, not model text or tokens. The first probe during rollout reached the old ready revision and had no `movie_reads` field; the repeat after readiness passed. The Stage 1 live-chat regression and explicit movie-read/denial test also passed on the new revision. Local tests: 51 passed.

The older synthetic image still has an admin PUT adapter beside FastMCP until the TMDB image replaces it. It is outside the MCP tool registry. Its Entra verifier required a valid signed v2 token for the catalog API audience, tenant, exact admin object ID, and `Catalog.Admin` application role. The admin identity and probe have since been removed; the repository's new TMDB deployment template contains no admin PUT configuration.

On 2026-10-18, the synthetic catalog was deployed as revision `ca-az-maf-movie-mcp--0000001`, image digest `sha256:209edec91beb1da58fd028601f7ea5a3a576c7f8d270f2d41f5963258c2b771d`, with internal ingress and one ready replica. The then-active admin identity authorized a complete replacement of `movie_000101`; the direct downstream PUT returned `200` and revision `1`. The temporary title was *Brass Comet Admin Test*. After the TMDB scope decision, the probe, its role assignment, and the managed identity were deleted. The old in-memory edit will disappear on MCP replacement.

The hosted agent's explicit read regression passed after this deployment: authenticated session and MCP get `200`, unauthenticated agent route `401`, and agent write proposal `403`. The planned synthetic read-after-write and direct downstream PUT checks did not run before the TMDB-only scope change and are no longer acceptance gates. Automatic approval review had stopped the initial follow-up command due to an account usage limit; it did not record a security result. TMDB-specific local and hosted results must be recorded separately.

Controlled outbound destination blocking and the remaining deployed network exercises are still required before Stage 2 acceptance. A `403` at the agent route is distinct from a denial by the downstream catalog service.
