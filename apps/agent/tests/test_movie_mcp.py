import pytest

from az_maf_agent.core import LOCAL, Service
from az_maf_agent.model import Denied
from az_maf_agent.movie_mcp import MovieMCPClient, validate_arguments, validate_result


async def test_real_fastmcp_read_and_forbidden_write(settings):
    client = MovieMCPClient()
    service = Service(settings, movie_client=client, audit=lambda event: None)
    sid = service.create(LOCAL)["session_id"]
    try:
        result = await service.movie_read(LOCAL, sid, "get_movie", {"catalog_id": "movie_000103"})
        assert result["movie"]["title"] == "The Last Lantern"
        with pytest.raises(Denied, match="tool_not_allowed"):
            await service.movie_read(LOCAL, sid, "put_movie", {"catalog_id": "movie_000103"})
        client.revoke("get_movie")
        with pytest.raises(Denied, match="tool_not_allowed"):
            await service.movie_read(LOCAL, sid, "get_movie", {"catalog_id": "movie_000103"})
        assert service.sessions[sid].movie_reads == 2
    finally:
        await service.close()


def test_tool_arguments_and_results_fail_closed():
    with pytest.raises(Denied, match="invalid_tool_arguments"):
        validate_arguments("search_movies", {"query": "x", "limit": 11})
    with pytest.raises(Denied, match="invalid_tool_arguments"):
        validate_arguments("get_movie", {"catalog_id": "movie_000103", "url": "https://other"})
    with pytest.raises(Denied, match="invalid_tool_result"):
        validate_result(
            "get_movie",
            {
                "catalog_version": "synthetic-movies-v1",
                "catalog_revision": 0,
                "movie": {
                    "id": "movie_000103",
                    "title": "Bad",
                    "year": 2020,
                    "genre": "drama",
                    "synopsis": "x" * 1001,
                    "synthetic_rating": 5.0,
                },
            },
        )
