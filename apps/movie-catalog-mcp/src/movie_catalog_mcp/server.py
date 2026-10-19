"""Authenticated FastMCP server exposing only TMDB movie reads."""

import os
from uuid import UUID

import uvicorn
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token

from .contracts import Denied, WorkloadIdentity
from .tmdb import TMDBClient, TMDBDispatcher

MCP_RUNTIME = WorkloadIdentity("movie-catalog-mcp", "catalog-reader")
_dispatcher: TMDBDispatcher | None = None


def _hosted_settings():
    if os.environ.get("MOVIE_MCP_MODE") != "http":
        return None
    tenant = str(UUID(os.environ["MCP_TENANT_ID"]))
    audience = str(UUID(os.environ["MCP_AUDIENCE"]))
    agent_oid = str(UUID(os.environ["MCP_ALLOWED_AGENT_OID"]))
    return tenant, audience, agent_oid


_hosted = _hosted_settings()
if _hosted:
    _tenant, _audience, _agent_oid = _hosted
    _verifier = JWTVerifier(
        jwks_uri=f"https://login.microsoftonline.com/{_tenant}/discovery/v2.0/keys",
        issuer=f"https://login.microsoftonline.com/{_tenant}/v2.0",
        audience=_audience,
        algorithm="RS256",
    )
else:
    _verifier = None

mcp = FastMCP("TMDB Movie Search", auth=_verifier)


def _reader() -> WorkloadIdentity:
    if _hosted:
        token = get_access_token()
        claims = token.claims if token else {}
        roles = claims.get("roles")
        if (
            claims.get("tid") != _tenant
            or claims.get("oid") != _agent_oid
            or not isinstance(roles, list)
            or "Catalog.Read" not in roles
        ):
            raise Denied("tool_permission_denied")
    return MCP_RUNTIME


def _catalog() -> TMDBDispatcher:
    global _dispatcher
    if _dispatcher is None:
        token = os.environ.get("TMDB_API_READ_ACCESS_TOKEN", "")
        if not token:
            raise Denied("tmdb_not_configured")
        _dispatcher = TMDBDispatcher(TMDBClient(token), frozenset({MCP_RUNTIME}))
    return _dispatcher


@mcp.tool
def search_movies(query: str, limit: int = 5) -> dict:
    """Search TMDB movie titles, returning at most ten non-adult records."""
    reader = _reader()
    return _catalog().dispatch(reader, "search_movies", {"query": query, "limit": limit})


@mcp.tool
def get_movie(catalog_id: str) -> dict:
    """Get TMDB details for a tmdb_<id> movie ID."""
    reader = _reader()
    return _catalog().dispatch(reader, "get_movie", {"catalog_id": catalog_id})


app = mcp.http_app(path="/mcp") if _hosted else None


def main() -> None:
    if _hosted:
        uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)
    else:
        mcp.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
