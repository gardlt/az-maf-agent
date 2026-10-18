"""FastMCP read-only server for the synthetic movie catalog.

Only the two pinned read contracts are registered. The separate HTTP admin
adapter is intentionally absent from this server and cannot become an MCP tool
through discovery or approval.
"""

from fastmcp import FastMCP

from .catalog import Catalog, MovieDispatcher
from .contracts import WorkloadIdentity

MCP_RUNTIME = WorkloadIdentity("movie-catalog-mcp", "catalog-reader")
_dispatcher = MovieDispatcher(Catalog(), frozenset({MCP_RUNTIME}))

mcp = FastMCP("Synthetic Movie Catalog")


@mcp.tool
def search_movies(query: str, limit: int = 5) -> dict:
    """Search the bundled synthetic catalog by text, returning at most ten records."""
    return _dispatcher.dispatch(MCP_RUNTIME, "search_movies", {"query": query, "limit": limit})


@mcp.tool
def get_movie(catalog_id: str) -> dict:
    """Get one synthetic movie record by its stable movie_###### catalog ID."""
    return _dispatcher.dispatch(MCP_RUNTIME, "get_movie", {"catalog_id": catalog_id})


def main() -> None:
    """Run the read-only server using FastMCP's standard stdio transport."""
    mcp.run(transport="stdio")
