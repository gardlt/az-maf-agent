"""FastMCP read-only server for the synthetic movie catalog.

Only the two pinned read contracts are registered. The separate HTTP admin
adapter is intentionally absent from this server and cannot become an MCP tool
through discovery or approval.
"""

import os
from uuid import UUID

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token

from .catalog import Catalog, MovieDispatcher
from .contracts import Denied, WorkloadIdentity

MCP_RUNTIME = WorkloadIdentity("movie-catalog-mcp", "catalog-reader")
_dispatcher = MovieDispatcher(Catalog(), frozenset({MCP_RUNTIME}))


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
    _issuer = f"https://login.microsoftonline.com/{_tenant}/v2.0"
    _verifier = JWTVerifier(
        jwks_uri=f"https://login.microsoftonline.com/{_tenant}/discovery/v2.0/keys",
        issuer=_issuer,
        audience=_audience,
        algorithm="RS256",
    )
else:
    _verifier = None

mcp = FastMCP("Synthetic Movie Catalog", auth=_verifier)


def _reader() -> WorkloadIdentity:
    if _hosted:
        token = get_access_token()
        claims = token.claims if token else {}
        if (
            claims.get("tid") != _tenant
            or claims.get("oid") != _agent_oid
            or "Catalog.Read" not in claims.get("roles", [])
        ):
            raise Denied("tool_permission_denied")
    return MCP_RUNTIME


@mcp.tool
def search_movies(query: str, limit: int = 5) -> dict:
    """Search the bundled synthetic catalog by text, returning at most ten records."""
    return _dispatcher.dispatch(_reader(), "search_movies", {"query": query, "limit": limit})


@mcp.tool
def get_movie(catalog_id: str) -> dict:
    """Get one synthetic movie record by its stable movie_###### catalog ID."""
    return _dispatcher.dispatch(_reader(), "get_movie", {"catalog_id": catalog_id})


def main() -> None:
    """Run stdio locally or an authenticated HTTP server in the hosted app."""
    if _hosted:
        mcp.run(transport="http", host="0.0.0.0", port=8000, show_banner=False)
    else:
        mcp.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
