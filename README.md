# az-maf-agent — Stage 1 and Stage 2 foundation

A Python CLI and Microsoft Agent Framework chat core with bounded, process-local session history. The deterministic offline default requires **no Azure account or credentials** after dependencies are installed. Stage 2 includes a separate FastMCP movie catalog and an explicit agent-side read path. Model-generated tool calls, skills, durable memory, command execution, and agent catalog writes remain disabled.

This is a teaching implementation plus a single-replica authenticated API test deployment, **not a production-ready service**. The [specification](docs/secure-agent-teaching-spec.md) and [stage tasks](docs/tasks/README.md) remain authoritative. The private registry images, infrastructure templates, and hosted evidence are documented in [the hosted runbook](docs/stage-1-hosted.md) and [Stage 2 validation](docs/stage-2-validation.md). Signed-in Stage 1 live-model chat and Stage 2 model-selected MCP reads have passed; deployed admin authorization and controlled-egress acceptance remain pending.

## Run locally

Use Python 3.12 and [uv](https://docs.astral.sh/uv/). This is a workspace monorepo: `apps/agent` owns the agent and `apps/movie-catalog-mcp` owns the catalog service. Dependencies and hashes are recorded in `uv.lock`.

```sh
uv sync --locked --all-packages
uv run --locked agent-chat
```

Enter `hello`, then another message: the fake client reports one, then two user messages in its bounded context. `/reset` clears conversation history; the next reply reports one message. `/quit` exits. Ctrl-C cancels the active run and exits with status 130. The fixed `offline/developer` identity is accepted only in local fake mode; there is no CLI option to assert another identity. The fake intentionally does not echo prompt content or pretend to answer real questions.

```sh
uv run --locked pytest -q
uv run --locked ruff check apps
uv run --locked ruff format --check apps
```

Startup/configuration/authentication failures exit 2. A denied interactive request reports a stable code and leaves history unchanged. No prompt/response text is written to audit logs. Do not paste credentials or personal data into this teaching app: minimization is not a general-purpose data-loss prevention system.

## Configuration and budgets

`config/offline.json` specifies **every required limit** and policy version. An explicit `--config PATH` is required when using a different configuration; partial files, unknown fields, non-finite limits, and unsupported live configuration fail closed. Defaults come from the spec. Session-only additions are 30-minute idle TTL, four-hour maximum lifetime, 32 KiB/8,000 conservative history units, and at most 1,000 sessions; these are documented teaching choices, not approved production retention settings.

A run is one user submission. A model attempt, including each retry, consumes its run turn/token/spend allowance. Context uses UTF-8 bytes plus framing allowance as a conservative text-token estimate; output has both the provider token cap and a conservative UTF-8 byte cap. This can reject text that would fit an exact tokenizer. Validate this bound against the actual selected model before live acceptance, or implement a model-specific tokenizer with reviewed bounds. No model is selected or hardcoded.

Daily per-principal cost reservations are kept separately from history. Reset and cancellation never refund ambiguous charges. Known usage is recorded alongside reserved totals; reservations remain conservatively charged rather than refunded. Billing can outlive request cancellation. Counters are RAM-only: restart loses daily accounting, so live production use requires the future shared authoritative ledger. The fake is free and makes no network calls.

## Sessions and concurrency

`Agent` uses an explicitly configured `InMemoryHistoryProvider` and `AgentSession`. The provider stores only user/assistant text. Old complete message pairs are trimmed to fit history and request limits; summarization is deliberately not implemented. Instruction-like text stays untrusted regardless of its role in history. Authority, counters, revision, and cancellation state are outside model context.

Each session is owned by a verified tenant/user, has a server-generated ID and revision, and allows one active update. Chat requires the expected revision; successful duplicate/stale submissions fail. Reset or cancel invalidates active work. A run edits a private snapshot and commits only if the session is still current and unexpired. No late successful response can resurrect reset history. Expired sessions are inaccessible and are purged on the next service operation; this is lazy RAM cleanup, not a background physical-erasure SLA.

This version supports **one process only**: restart loses sessions, and unknown IDs return not-found. Do not run multiple workers/replicas or rely on sticky routing. A shared TTL session store and distributed budget/control state remain open decisions. Failed requests may be retried with the same revision, but every model attempt still consumes budgets. There is no durable idempotency store or cross-restart resumption.

## Minimal hosted boundary

The selected path remains CLI → HTTPS Container Apps ingress with Entra Easy Auth → Python API → shared agent core. A dedicated Azure test foundation and fake-mode API are deployed. FastAPI supplies a small HTTP adapter; it does not replace Easy Auth. The adapter **also verifies the original Entra v2 bearer token** against the configured issuer/audience/signature/time claims, requires delegated `Chat.Access`, and enforces a configured user-object-ID allowlist. It never trusts `X-MS-CLIENT-PRINCIPAL`, identity in JSON, or a CLI claim of tenant/user. Thus directly reaching this API does not turn a forged header into identity.

Configure before hosted testing:

1. Register the API with the intended tenant, v2 tokens, exposed `Chat.Access` scope, and permitted client/consent. Set `ENTRA_TENANT_ID`, `ENTRA_AUDIENCE`, and comma-separated `ENTRA_ALLOWED_USERS` object IDs from approved configuration. Public identifier examples are not credentials.
2. Configure Easy Auth with the same issuer/audience and unauthenticated `Return401`; use [config/easyauth.example.json](config/easyauth.example.json) as an **unapplied template**, replacing placeholders and checking current Azure schema. Configure ingress `allowInsecure: false`. Do not expose an alternate unauthenticated ingress. The application accepts original bearer tokens, not Easy Auth session cookies or session-token exchange headers.
3. Use one replica/process for this limited test deployment; do not claim shared accounting/resumption. Run `uvicorn az_maf_agent.api:from_env --factory --host 0.0.0.0 --port 8000 --workers 1 --limit-concurrency 32 --no-access-log` behind the HTTPS ingress. Set `AGENT_CONFIG` to the approved JSON file. A fake-mode API still requires real Entra authentication; there is no server development-auth bypass.
4. For a live model, copy the complete offline configuration and set `mode: "azure"`, approved `endpoint` (an HTTPS `*.openai.azure.com` resource origin), `deployment`, `api_version`, `model_context_tokens`, and explicit input/output USD-per-million prices. Select a deployment compatible with text chat completions, `max_completion_tokens`, and the usage accounting contract. Do not put API keys in configuration. This deliberately narrow adapter is not a claim of support for all Azure model endpoints.
5. Assign a dedicated Container Apps managed identity with least-privilege model inference access; optionally configure its client ID. No local CLI identity or user token is forwarded to the model. Key Vault-backed references are required if a future dependency needs a secret. This implementation uses managed identity and contains no downstream key fallback.
6. Copy the complete offline configuration to a private client configuration file and run `agent-chat --config PATH --api https://YOUR_APPROVED_API`. The first hosted use opens the Stage 1 device-code flow; later runs silently refresh the encrypted, OS-user-scoped token cache using a local account selector. `AGENT_ACCESS_TOKEN` remains an optional automation override and must never be passed on the command line or committed. The client distinguishes 401 reauthentication from 403 denial. Ctrl-C requests server cancellation; an unconfirmed cancellation is reported and server deadlines remain in effect.

API routes: `POST /sessions`, `POST /sessions/{id}/chat` with `{"text":"hello","revision":0}`, and `POST /sessions/{id}/reset` or `/cancel`. With Stage 2 enabled, `POST /sessions/{id}/movies/{tool_name}` adds only the pinned catalog reads. There are no operator, file, or memory routes. Request bodies and ingestion time are bounded. OpenAPI/docs routes are disabled. All functional routes require authentication; errors omit raw invalid input/provider payloads.

## Stage 2 local catalog foundation

`az_maf_agent.catalog` packages `synthetic-movies-v1`, a small invented catalog with stable `movie_` IDs and clearly labeled `synthetic_rating` values. The pinned dispatcher permits only `search_movies(query, limit)` and `get_movie(catalog_id)` for explicitly approved principals. It rejects unknown tools and arguments, pagination, URLs, paths, credential selectors, malformed records, and revoked tools before any catalog result is returned. Results have validated record fields, deterministic ordering, a truncation flag, and an 8 KiB serialized-result cap.

The local exercise also includes a separate `PUT /movies/{catalog_id}` adapter backed by an injected, service-specific verified-principal dependency. Only its configured test/admin principal can replace an existing complete synthetic record with a matching ID; the local agent/MCP reader identity receives `403`, including on a direct request, and denied writes leave the catalog revision unchanged. This adapter is not configured for deployment authentication or public ingress.

`movie-catalog-mcp` now exposes these two read operations through a FastMCP server over its standard stdio transport. Run it locally with `uv run --locked movie-catalog-mcp`. The separate admin PUT adapter is not registered with FastMCP.

Run `uv run --locked agent-chat --movies` to use `/search QUERY` and `/movie movie_######` through the agent's pinned FastMCP client. The authenticated `POST /sessions/{id}/movies/{tool_name}` API path is enabled in the hosted agent. The agent validates the advertised tool contract and each result, checks session ownership and a per-session read limit, and can revoke a tool before dispatch. The local MCP subprocess receives a minimal environment. The hosted agent also enables an opt-in, bounded model tool loop for these two reads; `uv run --locked python scripts/test_movie_model_tools.py` verifies a live model-selected MCP lookup without printing model text or tokens.

The internal FastMCP app runs in the existing Container Apps environment with separate identity and Entra application-role authentication. An approved hosted read passed, as did unauthenticated caller and write-proposal denials. Outbound network enforcement and the remaining deployed network checks are still required before Stage 2 can be accepted. See [Stage 2 validation](docs/stage-2-validation.md).

To exercise the deployed app, run `uv run --locked python scripts/test_container_app.py`. It starts a device-code flow only when the encrypted Stage 1 cache cannot refresh a token or `AGENT_ACCESS_TOKEN` is unset, prints only selected token claims, and checks unauthenticated rejection, session creation, chat, stale revision denial, and reset. It neither logs nor writes the bearer token.

Run `uv run --locked python scripts/test_movie_container_app.py` to check the deployed movie read and denial path with the same cached sign-in.

Validate live tokens, real Easy Auth behavior, workload RBAC, endpoint compatibility, exported telemetry, and ingress restrictions in Azure before marking hosted acceptance passed. The local RSA-signed token tests prove application checks, not an Azure deployment. SDK/platform tracing must stay disabled or undergo the spec's sensitive-content review. Do not enable content capture. Library logging is suppressed by both entry points. Startup rejects explicit message-content capture; keep hosted diagnostic levels and platform trace settings under review.

## Architecture decisions and remaining work

- Python 3.12, Agent Framework core 1.22.0, FastAPI and a minimal text-only `BaseChatClient` are the Stage 1 foundation. Stage 2 model-selected reads use a separate application-owned Chat Completions loop with explicit tool validation and the same service budgets. An SDK provider client is an alternative if its automatic retries, history, tools, and telemetry can be bounded equivalently.
- RAM history and trimming keep the local lesson small. Reconsider shared TTL storage for multiple replicas/resumption; reconsider summarization only after testing poisoning and budgets. Durable memory remains Stage 4.
- JWT verification supplements Easy Auth to avoid relying on spoofable headers during local API tests or accidental alternate ingress. It adds a JWKS dependency; review a platform-only trust adapter only when its network boundary is demonstrably enforced.
- A single configured Azure deployment is supported; model choice, API deployment/version, pricing, session backend, and distributed control product remain open. Foundry hosting, API Management, and runtime model routing remain future options.
- The fake-mode image is in the private test registry and the API runs in Azure. Registry provenance beyond its recorded digest, distributed controls, egress enforcement, non-cooperative-worker termination, durable audit, secret rotation drills, signed-in hosted acceptance, and live-model evaluation are not demonstrated here.

See [Stage 1 validation](docs/stage-1-validation.md) for evidence and incomplete gates. Subsequent stages must preserve these tests and the spec's read-only agent catalog policy.

See [the change log](docs/change-log.md) for a committed record of material deployment, authentication, and hosted-test changes.
