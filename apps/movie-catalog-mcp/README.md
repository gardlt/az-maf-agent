# Movie catalog MCP

The `movie-catalog-mcp` package is a FastMCP service exposing two read-only TMDB movie tools. It runs locally over stdio or as an authenticated HTTP service for the [agent application](../agent/README.md). It contains no model inference or movie write operations.

## Tools

| Tool | Arguments | Result |
| --- | --- | --- |
| `search_movies` | `query`: 1–120 characters after trimming, at most 480 UTF-8 bytes; `limit`: 1–10, default 5 | Matching movies and a `truncated` flag |
| `get_movie` | `catalog_id`: a `tmdb_<id>` identifier, such as `tmdb_603` | One movie or a `not_found` result |

Responses use `catalog_version: "tmdb-v1"`. Movie records include `id`, `title`, `year`, `synopsis`, `tmdb_rating`, and `source: "TMDB"`.

The adapter requests English-language results, excludes adult movies, and searches only the first TMDB results page. It pins the upstream origin and read paths, disables redirects, uses a five-second timeout, and limits upstream responses to 128 KiB and search results to 8 KiB.

## Local setup

Use Python 3.12 and `uv`. Run all commands below from the **repository root**:

```sh
uv sync --locked --all-packages
```

Supply a TMDB API Read Access Token securely through `TMDB_API_READ_ACCESS_TOKEN`. The server reads this environment variable on the first tool call; a missing token produces `tmdb_not_configured`. See the [TMDB integration guide](../../docs/tmdb-integration.md) for credential details.

With `MOVIE_MCP_MODE` unset, start the stdio service:

```sh
uv run --locked movie-catalog-mcp
```

This command waits for an MCP client to communicate over stdin/stdout; it is not an interactive chat prompt. For a terminal demonstration, use the agent, which starts the stdio subprocess automatically:

```sh
uv run --locked agent-chat --movies
```

Then enter `/search The Matrix` or `/movie tmdb_603`. Ordinary chat remains on the fake model; explicit movie commands make real TMDB requests.

## HTTP service

Set these environment variables **before starting the process**:

| Variable | Purpose |
| --- | --- |
| `MOVIE_MCP_MODE` | Set exactly to `http` to enable authenticated HTTP transport |
| `TMDB_API_READ_ACCESS_TOKEN` | TMDB bearer credential |
| `MCP_TENANT_ID` | Entra tenant UUID |
| `MCP_AUDIENCE` | MCP application audience UUID |
| `MCP_ALLOWED_AGENT_OID` | Allowed calling agent's object UUID |

```sh
uv run --locked movie-catalog-mcp
```

HTTP mode listens on `0.0.0.0:8000` at `/mcp`. It validates Entra JWT signatures, issuer, and audience, then requires the configured tenant, agent object ID, and `Catalog.Read` role before each tool dispatch. Stdio mode has no Entra verifier.

The hosted agent connects through HTTPS to a private Container Apps ingress. Configure that deployment using the [agent-to-MCP architecture](../../docs/architecture-review/02-agent-to-mcp.md), [environment variable guide](../../docs/dev-environment-variables.md), and [deployment guide](../../docs/github-actions-deployment.md).

Build the image from the repository root:

```sh
docker build -f Dockerfile.mcp -t movie-catalog-mcp .
```

The image sets `MOVIE_MCP_MODE=http`, exposes port 8000, and starts `movie-catalog-mcp`. Supply the remaining environment variables and TMDB secret through the deployment configuration.

## Development

```sh
uv run --locked pytest -q apps/movie-catalog-mcp/tests
uv run --locked ruff check apps/movie-catalog-mcp
uv run --locked ruff format --check apps/movie-catalog-mcp
```

Tests use mocked HTTP responses and do not need TMDB credentials.

| File | Responsibility |
| --- | --- |
| [server.py](src/movie_catalog_mcp/server.py) | FastMCP tools, transport selection, and Entra authorization |
| [tmdb.py](src/movie_catalog_mcp/tmdb.py) | Bounded TMDB requests, normalized results, and dispatch authorization |
| [contracts.py](src/movie_catalog_mcp/contracts.py) | Workload identity and public denial codes |
| [test_tmdb.py](tests/test_tmdb.py) | Adapter and dispatcher tests |

Agent-side MCP contract and transport tests live in [apps/agent/tests](../agent/tests/).

## Attribution

This product uses the TMDB API but is not endorsed or certified by TMDB. See [Credits](../../docs/credits.md) for the logo and attribution, and the [integration guide](../../docs/tmdb-integration.md) for the project's non-commercial usage context.
