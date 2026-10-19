"""Pinned, read-only TMDB movie API adapter.

This adapter makes only the documented v3 search and movie-details requests.
TMDB's API Read Access Token also authenticates these endpoints from a v4
account; no TMDB user session or write permission is needed.
"""

import json
import re
from datetime import date

import httpx

from .contracts import Denied, WorkloadIdentity

TMDB_ORIGIN = "https://api.themoviedb.org"
MAX_RESPONSE_BYTES = 131_072
MAX_RESULT_BYTES = 8_192
MAX_QUERY_BYTES = 480
MAX_MOVIE_ID = 2_147_483_647


class TMDBError(Exception):
    """A safe public error code without upstream payloads or credentials."""


class TMDBClient:
    def __init__(self, token: str, transport: httpx.BaseTransport | None = None):
        if not token or any(char.isspace() for char in token):
            raise ValueError("TMDB API Read Access Token required")
        self.client = httpx.Client(
            base_url=TMDB_ORIGIN,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=5.0,
            follow_redirects=False,
            transport=transport,
        )

    def close(self) -> None:
        self.client.close()

    def _get(self, path: str, params: dict[str, object]) -> dict:
        try:
            with self.client.stream("GET", path, params=params) as response:
                if response.status_code == 404:
                    raise TMDBError("not_found")
                if response.status_code == 429:
                    raise TMDBError("rate_limited")
                if response.status_code != 200:
                    raise TMDBError("upstream_unavailable")
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_RESPONSE_BYTES:
                        raise TMDBError("upstream_result_too_large")
            value = json.loads(data)
            if not isinstance(value, dict):
                raise ValueError("expected object")
            return value
        except TMDBError:
            raise
        except (httpx.HTTPError, ValueError, UnicodeDecodeError):
            raise TMDBError("upstream_unavailable") from None

    @staticmethod
    def _movie(value: object) -> dict:
        if not isinstance(value, dict) or value.get("adult") is not False:
            raise TMDBError("invalid_movie_result")
        movie_id = value.get("id")
        title = value.get("title")
        overview = value.get("overview")
        released = value.get("release_date")
        rating = value.get("vote_average")
        if (
            type(movie_id) is not int
            or not 1 <= movie_id <= MAX_MOVIE_ID
            or not isinstance(title, str)
            or not title.strip()
            or not isinstance(overview, str)
            or not isinstance(released, str)
            or not isinstance(rating, (int, float))
            or isinstance(rating, bool)
            or not 0 <= rating <= 10
        ):
            raise TMDBError("invalid_movie_result")
        year = None
        if released:
            try:
                year = date.fromisoformat(released).year
            except ValueError:
                raise TMDBError("invalid_movie_result") from None
        return {
            "id": f"tmdb_{movie_id}",
            "title": title.strip()[:200],
            "year": year,
            "synopsis": overview[:1000],
            "tmdb_rating": float(rating),
            "source": "TMDB",
        }

    def search(self, query: str, limit: int = 5) -> dict:
        if (
            not isinstance(query, str)
            or not 1 <= len(query.strip()) <= 120
            or len(query.encode("utf-8")) > MAX_QUERY_BYTES
            or type(limit) is not int
            or not 1 <= limit <= 10
        ):
            raise TMDBError("invalid_tool_arguments")
        data = self._get(
            "/3/search/movie",
            {"query": query.strip(), "include_adult": "false", "language": "en-US", "page": 1},
        )
        raw = data.get("results")
        total = data.get("total_results")
        if not isinstance(raw, list) or type(total) is not int or total < 0:
            raise TMDBError("invalid_movie_result")
        movies = []
        for item in raw:
            if isinstance(item, dict) and item.get("adult") is True:
                continue
            movies.append(self._movie(item))
            candidate = {"catalog_version": "tmdb-v1", "movies": movies, "truncated": True}
            if len(json.dumps(candidate, ensure_ascii=False).encode("utf-8")) > MAX_RESULT_BYTES:
                movies.pop()
                break
            if len(movies) == limit:
                break
        return {"catalog_version": "tmdb-v1", "movies": movies, "truncated": total > len(movies)}

    def get(self, catalog_id: str) -> dict:
        if not isinstance(catalog_id, str) or not re.fullmatch(r"tmdb_[1-9][0-9]{0,9}", catalog_id):
            raise TMDBError("invalid_tool_arguments")
        movie_id = int(catalog_id[5:])
        if movie_id > MAX_MOVIE_ID:
            raise TMDBError("invalid_tool_arguments")
        try:
            data = self._get(f"/3/movie/{movie_id}", {"language": "en-US"})
        except TMDBError as exc:
            if str(exc) == "not_found":
                return {"catalog_version": "tmdb-v1", "not_found": True, "catalog_id": catalog_id}
            raise
        movie = self._movie(data)
        if movie["id"] != catalog_id:
            raise TMDBError("invalid_movie_result")
        return {"catalog_version": "tmdb-v1", "movie": movie}


class TMDBDispatcher:
    """Authorize the two pinned read operations before contacting TMDB."""

    def __init__(self, client: TMDBClient, readers: frozenset[WorkloadIdentity]):
        if not readers:
            raise ValueError("approved readers required")
        self.client = client
        self.readers = readers
        self.revoked: set[str] = set()

    def revoke(self, name: str) -> None:
        self.revoked.add(name)

    def dispatch(self, principal: WorkloadIdentity, name: object, arguments: object) -> dict:
        if principal not in self.readers:
            raise Denied("tool_permission_denied")
        if not isinstance(name, str) or name in self.revoked:
            raise Denied("tool_not_allowed")
        if not isinstance(arguments, dict):
            raise Denied("invalid_tool_arguments")
        try:
            if name == "search_movies" and set(arguments) <= {"query", "limit"}:
                return self.client.search(**arguments)
            if name == "get_movie" and set(arguments) == {"catalog_id"}:
                return self.client.get(arguments["catalog_id"])
        except (TMDBError, TypeError) as exc:
            raise Denied(
                str(exc) if isinstance(exc, TMDBError) else "invalid_tool_arguments"
            ) from None
        raise Denied("tool_not_allowed")
