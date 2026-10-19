# TMDB movie data integration

TMDB is the sole movie source for the MCP. The hosted agent and MCP now run the TMDB-aware images, with the TMDB credential referenced as a Container App secret. A live local search/details check and hosted agent-to-MCP reads passed on 2026-10-18; see the [validation record](stage-2-validation.md). The repository implementation uses `movie_catalog_mcp.tmdb.TMDBClient` for the two MCP read tools, and its local tests use mocked HTTP responses.

## API and credential

TMDB's [application authentication guide](https://developer.themoviedb.org/docs/authentication-application) says an API Read Access Token can be sent as a bearer token to both v3 and v4 methods. Movie [search](https://developer.themoviedb.org/reference/search-movie) and [details](https://developer.themoviedb.org/reference/movie-details) are v3 endpoints, even when the token comes from the v4 account settings. The adapter calls only `GET https://api.themoviedb.org/3/search/movie` and `GET https://api.themoviedb.org/3/movie/{id}`. It does not request a TMDB user session or perform a write.

The token is supplied to the MCP workload as a Container App secret or locally as `TMDB_API_READ_ACCESS_TOKEN`. Do not put it in Git, committed Bicep parameters, client arguments, logs, or chat. The current Container Apps environment permits the successful TMDB requests but has no controlled-egress network policy; that remains a separate Stage 2 acceptance gap.

The adapter pins the API origin and paths, disables redirects, sets a five-second timeout, caps response bodies at 128 KiB, requests only English-language non-adult search results from the first page, and returns at most ten normalized records. It treats `429` as a rate-limit failure and returns no upstream body or credential in its error. TMDB [documents that limits can change and `429` must be respected](https://developer.themoviedb.org/docs/rate-limiting).

## Contract decision

The two MCP tools and agent client use `tmdb_<id>` IDs, `tmdb-v1`, and `tmdb_rating` with `source: "TMDB"`; they do not relabel a TMDB rating as synthetic. The synthetic admin PUT flow has been removed from the repository because TMDB is an external read-only source. The previously deployed synthetic admin probe, role assignment, and identity have been removed. The old Stage 2 write/read-after-write acceptance criterion is superseded by downstream read-only and egress checks; historical validation remains in the change log.

## Attribution and release gate

TMDB's [FAQ](https://developer.themoviedb.org/docs/faq) requires attribution and a notice that the product uses the TMDB API but is not endorsed or certified by TMDB. It also calls for an approved TMDB logo and distinguishes non-commercial from commercial use. The user confirmed this is a non-commercial teaching project on 2026-10-18. The repository [Credits](credits.md) page includes an approved logo and the required notice, and the CLI displays the notice when movie mode starts. Any separate user-facing hosted client must also show the credits; the API alone is not an About/Credits interface. Do not present TMDB data as part of the synthetic fixture.
