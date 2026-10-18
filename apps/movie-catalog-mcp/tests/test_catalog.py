import pytest

from movie_catalog_mcp.catalog import CATALOG_VERSION, Catalog, CatalogAdminService, MovieDispatcher
from movie_catalog_mcp.contracts import Denied, WorkloadIdentity
from movie_catalog_mcp.server import get_movie, mcp, search_movies

AGENT = WorkloadIdentity("agent-test", "catalog-reader")


def dispatcher():
    return MovieDispatcher(Catalog(), frozenset({AGENT}))


def test_search_and_get_are_deterministic_and_bounded():
    result = dispatcher().dispatch(AGENT, "search_movies", {"query": "  a  ", "limit": 2})
    assert result["catalog_version"] == CATALOG_VERSION
    assert result["truncated"] is True
    assert [movie["id"] for movie in result["movies"]] == ["movie_000101", "movie_000102"]
    assert (
        dispatcher().dispatch(AGENT, "get_movie", {"catalog_id": "movie_000103"})["movie"]["genre"]
        == "mystery"
    )
    assert dispatcher().dispatch(AGENT, "get_movie", {"catalog_id": "movie_999999"}) == {
        "catalog_version": CATALOG_VERSION,
        "catalog_revision": 0,
        "not_found": True,
        "catalog_id": "movie_999999",
    }


async def test_fastmcp_tools_only_expose_pinned_read_contracts():
    assert {tool.name for tool in await mcp.list_tools()} == {"get_movie", "search_movies"}
    assert search_movies("lantern")["movies"][0]["id"] == "movie_000103"
    assert get_movie("movie_000104")["movie"]["genre"] == "family"


@pytest.mark.parametrize(
    "tool,arguments",
    [
        ("search_movies", {"query": "", "limit": 5}),
        ("search_movies", {"query": "x", "limit": 11}),
        ("search_movies", {"query": "x", "page": 2}),
        ("get_movie", {"catalog_id": "movie_12"}),
        ("get_movie", {"catalog_id": "movie_000101", "url": "https://elsewhere"}),
        ("unknown", {}),
    ],
)
def test_invalid_arguments_and_unknown_tools_fail_closed(tool, arguments):
    with pytest.raises(Denied, match="tool_not_allowed|invalid_tool_arguments"):
        dispatcher().dispatch(AGENT, tool, arguments)


def test_permission_and_revocation_precede_dispatch():
    tools = dispatcher()
    with pytest.raises(Denied, match="tool_permission_denied"):
        tools.dispatch(
            WorkloadIdentity("other", "catalog-reader"), "get_movie", {"catalog_id": "movie_000101"}
        )
    tools.revoke("get_movie")
    with pytest.raises(Denied, match="tool_not_allowed"):
        tools.dispatch(AGENT, "get_movie", {"catalog_id": "movie_000101"})


def test_malicious_or_malformed_baseline_is_rejected():
    with pytest.raises(Exception):
        Catalog(
            [
                {
                    "id": "movie_000111",
                    "title": "Bad",
                    "year": 2010,
                    "genre": "mystery",
                    "synopsis": "x" * 1001,
                    "synthetic_rating": 4.0,
                }
            ]
        )


def test_admin_only_replacement_does_not_grant_agent_write_access():
    catalog = Catalog()
    admin = WorkloadIdentity("catalog-admin", "catalog-admin")
    service = CatalogAdminService(catalog, frozenset({admin}))
    original = catalog.get({"catalog_id": "movie_000101"})
    replacement = original["movie"] | {"title": "Brass Comet: Revised"}
    with pytest.raises(Denied, match="catalog_write_denied"):
        service.put(AGENT, "movie_000101", replacement)
    assert catalog.get({"catalog_id": "movie_000101"}) == original
    updated = service.put(admin, "movie_000101", replacement)
    assert updated["catalog_revision"] == 1
    assert updated["movie"]["title"] == "Brass Comet: Revised"


def test_admin_replacement_rejects_unknown_or_mismatched_ids_without_mutation():
    catalog = Catalog()
    admin = WorkloadIdentity("catalog-admin", "catalog-admin")
    service = CatalogAdminService(catalog, frozenset({admin}))
    replacement = catalog.get({"catalog_id": "movie_000101"})["movie"]
    with pytest.raises(Denied, match="catalog_write_denied"):
        service.put(admin, "movie_999999", replacement)
    with pytest.raises(Denied, match="catalog_write_denied"):
        service.put(admin, "movie_000102", replacement)
    assert catalog.revision == 0
