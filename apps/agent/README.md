# Agent CLI and API

The `az-maf-agent` package runs the movie assistant: a terminal client, an authenticated FastAPI service, and a governed Microsoft Agent Framework runtime. It combines bounded conversations, model routing, read-only movie tools, reviewed skills, consented preferences, and operational controls.

The separate [movie catalog MCP application](../movie-catalog-mcp/README.md) supplies TMDB reads. See the [repository overview](../../README.md) for the system architecture.

## Local setup

Use Python 3.12 and `uv`. Run all commands below from the **repository root**, since the default configuration and skill paths are relative to that directory.

```sh
uv sync --locked --all-packages
uv run --locked agent-chat
```

The default configuration is [config/offline.json](../../config/offline.json). It uses a deterministic fake model and needs no Azure credentials. The fake demonstrates conversation state and limits; it does not answer real questions.

| Command | Behavior |
| --- | --- |
| `/reset` | Clear conversation history while retaining usage accounting |
| `/quit` | Exit the client |
| Ctrl-C | Cancel the active run and exit |

To enable explicit local movie reads, supply `TMDB_API_READ_ACCESS_TOKEN` securely in the environment, then run:

```sh
uv run --locked agent-chat --movies
```

Use `/search The Matrix` or `/movie tmdb_603`. The client starts the MCP package as a local stdio subprocess; both workspace packages must be installed. These commands contact TMDB even though ordinary chat still uses the fake model.

## Hosted client

Connect to an approved HTTPS API:

```sh
uv run --locked agent-chat --api https://YOUR_APPROVED_AGENT_API --movies
```

The built-in device-code login uses the tenant, public client, and API scope configured in [client_auth.py](src/az_maf_agent/client_auth.py). These values must match your deployment. It keeps an encrypted, OS-user-scoped token cache. Alternatively, the client accepts a bearer token through `AGENT_ACCESS_TOKEN`.

Additional client options:

| Option or command | Purpose |
| --- | --- |
| `--config PATH` | Select a settings JSON file |
| `--session SESSION_ID` | Resume an owned hosted session |
| `--skill movie-research` or `--skill movie-night` | Request an enabled, reviewed hosted skill |
| `--skill-version VERSION` | Select the reviewed version; defaults to `1.0.0` |
| `/memory` | List saved preferences |
| `/remember preferred_genre comedy` | Explicitly consent to saving or correcting a preference for 30 days |
| `/remember preferred_language en` | Save or correct a language preference |
| `/forget ID` or `/forget all` | Delete saved preferences |

Skills and memory require the corresponding server configuration and permissions. Ordinary chat does not consent to saving preferences. Live model inference runs through the authenticated API.

## API configuration and deployment

The API factory is `az_maf_agent.api:from_env`. Its required environment variables are:

| Variable | Purpose |
| --- | --- |
| `AGENT_CONFIG` | Path to validated model, routing, and budget settings |
| `ENTRA_TENANT_ID` | Accepted Entra tenant |
| `ENTRA_AUDIENCE` | API token audience |
| `ENTRA_ALLOWED_USERS` | Comma-separated admitted user object IDs |

Optional features add their own required settings. For example, `ENABLE_MOVIE_MCP=true` requires `MCP_ENDPOINT` and `MCP_AUDIENCE`; hosted MCP endpoints must use the approved internal Container Apps URL ending in `/mcp`. `ENABLE_MOVIE_MODEL_TOOLS=true` enables model-driven movie tool use.

Use the [environment variable guide](../../docs/dev-environment-variables.md) and [hosted setup guide](../../docs/stages/stage-1/stage-1-hosted.md) to configure identities, inference, storage, and feature flags. With the environment configured, launch the API with:

```sh
uv run --locked uvicorn az_maf_agent.api:from_env --factory \
  --host 127.0.0.1 --port 8000 --workers 1 --limit-concurrency 32 --no-access-log
```

The hosted CLI requires HTTPS; the command above starts the application process without a TLS ingress. API routes cover sessions, chat, cancellation, movie reads, preferences, and approval simulations. See [api.py](src/az_maf_agent/api.py) for request schemas and [API/session architecture](../../docs/architecture-review/01-agent-api-sessions.md) for ownership and authentication.

The initial AG-UI transport is available at `POST /ag-ui` and is used by the local React
client in [apps/web](../web/README.md). Send the owned session ID as
`threadId` and the latest plain-text user message in the AG-UI `messages` array. The route
uses the session's current server-side revision and the same governed `Service.chat` path
as the hosted API. It emits AG-UI run/message lifecycle events and one completed text
delta; incremental token streaming and multimodal input are not supported yet. The route
does not execute frontend tools or accept client-provided state, context, or resume data.
See the [AG-UI integration plan](../../docs/ag-ui-integration-plan.md) for the follow-up
work and current limitations.

Build the service image from the repository root:

```sh
docker build -f Dockerfile -t az-maf-agent .
```

The image starts the API on port 8000. Follow the [deployment guide](../../docs/github-actions-deployment.md) for Azure configuration and deployment.

## Development

```sh
uv run --locked pytest -q apps/agent/tests
uv run --locked ruff check apps/agent
uv run --locked ruff format --check apps/agent
```

Key implementation areas under [src/az_maf_agent](src/az_maf_agent/):

| Files | Responsibility |
| --- | --- |
| `cli.py`, `client_auth.py`, `api.py` | Terminal client, login, and API boundary |
| `core.py`, `model.py`, `routing.py`, `model_tools.py` | Conversations, model calls, routing, and tool execution |
| `movie_mcp.py`, `skills.py`, `skill_control.py` | MCP client and reviewed skills |
| `memory.py`, `blob_memory.py`, `shared_sessions.py` | Preferences and shared conversation storage |
| `guardrails.py`, `guardrail_blob.py`, `supervisor.py` | Shared controls, accounting, and containment |

For operating procedures and known deployment gaps, see the [operator runbook](../../docs/stages/stage-5/stage-5-operator-runbook.md) and [architecture review](../../docs/architecture-review/README.md).
