import json

import httpx
import pytest
from fastmcp import Client

from movie_catalog_mcp import server
from movie_catalog_mcp.contracts import Denied
from movie_catalog_mcp.tmdb import TMDBClient, TMDBDispatcher, TMDBError


def sample(movie_id=11, title="Example Film"):
    return {
        "adult": False,
        "id": movie_id,
        "title": title,
        "overview": "An example overview.",
        "release_date": "2020-01-02",
        "vote_average": 7.5,
    }


def make_client(handler):
    return TMDBClient("test-secret", transport=httpx.MockTransport(handler))


def test_search_uses_only_pinned_read_request_and_bounded_result():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={"results": [sample(), sample(12, "Second Film")], "total_results": 2},
        )

    client = make_client(handler)
    try:
        result = client.search("  Example  ", limit=1)
    finally:
        client.close()
    request = requests[0]
    assert request.method == "GET"
    assert request.url.host == "api.themoviedb.org"
    assert request.url.path == "/3/search/movie"
    assert request.url.params["query"] == "Example"
    assert request.url.params["include_adult"] == "false"
    assert request.url.params["page"] == "1"
    assert request.headers["Authorization"] == "Bearer test-secret"
    assert result == {
        "catalog_version": "tmdb-v1",
        "movies": [
            {
                "id": "tmdb_11",
                "title": "Example Film",
                "year": 2020,
                "synopsis": "An example overview.",
                "tmdb_rating": 7.5,
                "source": "TMDB",
            }
        ],
        "truncated": True,
    }


def test_get_and_not_found():
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/3/movie/11"
        if request.url.params["language"] != "en-US":
            raise AssertionError("wrong language")
        return httpx.Response(200, json=sample())

    client = make_client(handler)
    try:
        assert client.get("tmdb_11")["movie"]["id"] == "tmdb_11"
    finally:
        client.close()

    missing = make_client(lambda _: httpx.Response(404))
    try:
        assert missing.get("tmdb_11") == {
            "catalog_version": "tmdb-v1",
            "not_found": True,
            "catalog_id": "tmdb_11",
        }
    finally:
        missing.close()


def test_invalid_input_and_upstream_redirect_fail_closed():
    client = make_client(lambda _: httpx.Response(302, headers={"Location": "https://elsewhere"}))
    try:
        with pytest.raises(TMDBError, match="invalid_tool_arguments"):
            client.search(" ")
        with pytest.raises(TMDBError, match="invalid_tool_arguments"):
            client.get("https://elsewhere")
        with pytest.raises(TMDBError, match="upstream_unavailable"):
            client.search("Example")
    finally:
        client.close()


def test_rate_limit_and_upstream_error_hide_response_body():
    for status, code in [(429, "rate_limited"), (503, "upstream_unavailable")]:
        client = make_client(lambda _: httpx.Response(status, text="private-upstream-detail"))
        try:
            with pytest.raises(TMDBError, match=code) as failure:
                client.search("Example")
            assert "private-upstream-detail" not in str(failure.value)
            assert "test-secret" not in str(failure.value)
        finally:
            client.close()


def test_malformed_detail_or_wrong_id_is_rejected():
    client = make_client(lambda _: httpx.Response(200, json=sample(movie_id=12)))
    try:
        with pytest.raises(TMDBError, match="invalid_movie_result"):
            client.get("tmdb_11")
    finally:
        client.close()


def test_adult_and_oversized_upstream_data_are_not_returned():
    adult = sample()
    adult["adult"] = True
    client = make_client(
        lambda _: httpx.Response(200, json={"results": [adult], "total_results": 1})
    )
    try:
        assert client.search("Example")["movies"] == []
    finally:
        client.close()

    oversized = make_client(
        lambda _: httpx.Response(
            200,
            content=json.dumps({"results": [sample() | {"overview": "x" * 132_000}]}).encode(),
        )
    )
    try:
        with pytest.raises(TMDBError, match="upstream_result_too_large"):
            oversized.search("Example")
    finally:
        oversized.close()


def test_search_result_stays_within_agent_byte_limit():
    records = [sample(i, f"Movie {i}") | {"overview": "a" * 1000} for i in range(1, 11)]
    client = make_client(
        lambda _: httpx.Response(200, json={"results": records, "total_results": 10})
    )
    try:
        result = client.search("Movie", limit=10)
        assert result["truncated"] is True
        assert len(result["movies"]) < 10
        assert len(json.dumps(result, ensure_ascii=False).encode()) <= 8192
    finally:
        client.close()


async def test_fastmcp_exposes_only_tmdb_reads(monkeypatch):
    client = make_client(lambda _: httpx.Response(200, json=sample()))
    dispatcher = TMDBDispatcher(client, frozenset({server.MCP_RUNTIME}))
    monkeypatch.setattr(server, "_dispatcher", dispatcher)
    try:
        async with Client(server.mcp) as mcp_client:
            assert {tool.name for tool in await mcp_client.list_tools()} == {
                "search_movies",
                "get_movie",
            }
            result = await mcp_client.call_tool("get_movie", {"catalog_id": "tmdb_11"})
            assert result.structured_content["movie"]["id"] == "tmdb_11"
        with pytest.raises(Denied, match="tool_not_allowed"):
            dispatcher.dispatch(server.MCP_RUNTIME, "put_movie", {"catalog_id": "tmdb_11"})
    finally:
        client.close()
