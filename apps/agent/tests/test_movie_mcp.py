import pytest

from az_maf_agent.core import LOCAL, Service
from az_maf_agent.model import Denied
from az_maf_agent.movie_mcp import validate_arguments, validate_result


class FakeMovieClient:
    def __init__(self):
        self.revoked = set()

    def revoke(self, name):
        self.revoked.add(name)

    async def read(self, name, arguments):
        if name in self.revoked or name != "get_movie":
            raise Denied("tool_not_allowed")
        return {
            "catalog_version": "tmdb-v1",
            "movie": {
                "id": arguments["catalog_id"],
                "title": "Star Wars",
                "year": 1977,
                "synopsis": "A movie.",
                "tmdb_rating": 8.2,
                "source": "TMDB",
            },
        }

    async def close(self):
        pass


async def test_tmdb_read_and_forbidden_write(settings):
    client = FakeMovieClient()
    service = Service(settings, movie_client=client, audit=lambda event: None)
    sid = service.create(LOCAL)["session_id"]
    try:
        result = await service.movie_read(LOCAL, sid, "get_movie", {"catalog_id": "tmdb_11"})
        assert result["movie"]["title"] == "Star Wars"
        with pytest.raises(Denied, match="tool_not_allowed"):
            await service.movie_read(LOCAL, sid, "put_movie", {"catalog_id": "tmdb_11"})
        client.revoke("get_movie")
        with pytest.raises(Denied, match="tool_not_allowed"):
            await service.movie_read(LOCAL, sid, "get_movie", {"catalog_id": "tmdb_11"})
        assert service.sessions[sid].movie_reads == 2
    finally:
        await service.close()


def test_tool_arguments_and_results_fail_closed():
    with pytest.raises(Denied, match="invalid_tool_arguments"):
        validate_arguments("search_movies", {"query": "x", "limit": 11})
    with pytest.raises(Denied, match="invalid_tool_arguments"):
        validate_arguments("get_movie", {"catalog_id": "tmdb_11", "url": "https://other"})
    with pytest.raises(Denied, match="invalid_tool_result"):
        validate_result(
            "get_movie",
            {
                "catalog_version": "tmdb-v1",
                "movie": {
                    "id": "tmdb_11",
                    "title": "Bad",
                    "year": 2020,
                    "synopsis": "x" * 1001,
                    "tmdb_rating": 5.0,
                    "source": "TMDB",
                },
            },
        )
