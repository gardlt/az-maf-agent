# Stage 2 validation — local and hosted MCP read path

On 2026-10-18, the agent called the separate `movie-catalog-mcp` package through FastMCP's stdio protocol. The agent accepts only the pinned `search_movies` and `get_movie` schemas, validates arguments before connecting, and revalidates the returned synthetic catalog record within an 8 KiB bound. Direct `put_movie` proposals are denied before dispatch. Revoking `get_movie` denies subsequent calls. The catalog's separate admin PUT contract remains outside MCP; local tests verify a reader identity cannot mutate its state.

Run the local exercise from the repository root:

```sh
uv sync --locked --all-packages
uv run --locked agent-chat --movies
```

In the CLI, enter `/search lantern`, `/movie movie_000103`, and `/quit`. The displayed rating is synthetic. The completed smoke test found *The Last Lantern* through both read operations. The test suite and lint commands are `uv run --locked pytest -q`, `uv run --locked ruff check apps`, and `uv run --locked ruff format --check apps`.

The separate MCP app `ca-az-maf-movie-mcp` now runs with internal ingress in the existing `cae-az-maf-stage1` environment. It uses its own system-assigned identity and accepts Entra v2 tokens for application ID `ddf8d97d-9b4a-4ce8-9fd2-a7293ad909cb`. The agent identity `71edeec2-8419-4709-9120-35b3f8f86067` has the `Catalog.Read` application role. The MCP verifies the token signature, issuer, audience, tenant, agent object ID, and role. The agent uses its managed identity for the MCP token and sends no user token downstream. The MCP image is pinned to digest `sha256:dd2db134a9031138fc65c24e96c921078944e0fcdabf0ecff98d8e0133996b77`; the agent image is pinned to `sha256:349926fdc0ddc20e226bb0df36eaed86315b1b7067e55f88db16be8b23ff2b85`.

On 2026-10-18, the hosted test against agent revision `ca-az-maf-stage1--0000009` recorded authenticated session creation `200`, unauthenticated movie read `401`, authenticated `get_movie(movie_000103)` `200`, and a `put_movie` proposal `403`. The returned record was *The Last Lantern* and its rating was explicitly labeled synthetic. A request to the internal MCP FQDN from outside the environment returned `404`. A direct request from inside the agent container to that MCP FQDN without a token returned `401`. Run the test with `uv run --locked python scripts/test_movie_container_app.py`; it uses the existing encrypted CLI token cache when available and never prints the token.

The live Container Apps environment has no VNet configuration or workload profiles. It cannot provide user-defined-route egress evidence in this form. [Azure's documented UDR support](https://learn.microsoft.com/en-us/azure/container-apps/use-azure-firewall) requires a workload profiles environment. Controlled outbound destination blocking and the remaining deployed network exercises therefore require a separately reviewed network foundation. The private MCP read path is hosted and proven; full Stage 2 network acceptance is not.

The agent now has an opt-in application-owned model tool loop. It advertises only the pinned `search_movies` and `get_movie` schemas to the configured Foundry model, validates each proposed call before dispatch, permits at most two sequential read attempts per run, charges each model attempt to the existing ledger, and stores only the final user/assistant text pair in session history. Tool results remain untrusted data, and the MCP reader permission is checked again at dispatch. It is enabled on the hosted agent by `ENABLE_MOVIE_MODEL_TOOLS=true`; the original text-only path remains available when disabled.

On 2026-10-18, agent revision `ca-az-maf-stage1--0000010` became ready with image digest `sha256:809c1982ff0e342e290274a786f92716eb9f46be1bf3a98fe2138fcc568bb211`. The signed-in `scripts/test_movie_model_tools.py` run recorded session creation `200`, live chat `200`, and exactly one completed MCP read for `movie_000103`. It printed only the answer length, not model text or tokens. The first probe during rollout reached the old ready revision and had no `movie_reads` field; the repeat after readiness passed. The Stage 1 live-chat regression and explicit movie-read/denial test also passed on the new revision. Local tests: 51 passed.

The admin PUT adapter is tested locally only and has not been deployed with independent service authentication. Controlled outbound destination blocking and direct downstream PUT denial are still required before Stage 2 acceptance.
