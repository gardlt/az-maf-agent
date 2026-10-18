"""Stage 2 synthetic movie catalog and guarded read-only dispatcher.

This module is intentionally local and deterministic.  It is not an IMDb
client, does not open network connections, and does not expose a generic tool
or HTTP interface.  A later host adapter may call this dispatcher only after
it establishes service identity and its separate network boundary.
"""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, field_validator

from .core import Principal
from .model import Denied

CATALOG_VERSION = "synthetic-movies-v1"
SERVER_ID = "synthetic-movie-catalog"
TOOL_VERSION = "1"
MAX_RESULT_BYTES = 8192
GENRES = frozenset({"action", "comedy", "drama", "family", "mystery", "science_fiction"})


class Movie(BaseModel):
    """The complete, bounded record returned by the catalog."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    id: Annotated[str, Field(pattern=r"^movie_[0-9]{6}$")]
    title: Annotated[str, Field(min_length=1, max_length=200)]
    year: Annotated[StrictInt, Field(ge=1888, le=2100)]
    genre: Literal["action", "comedy", "drama", "family", "mystery", "science_fiction"]
    synopsis: Annotated[str, Field(max_length=1000)]
    synthetic_rating: Annotated[StrictFloat, Field(ge=0, le=10)]

    @field_validator("title", "synopsis")
    @classmethod
    def no_control_characters(cls, value: str) -> str:
        if not value.strip() or any(ord(char) < 32 and char not in "\n\t" for char in value):
            raise ValueError("invalid text")
        return value


class SearchArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    query: Annotated[str, Field(min_length=1, max_length=120)]
    limit: Annotated[StrictInt, Field(ge=1, le=10)] = 5

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("empty query")
        if len(value.encode("utf-8")) > 480:
            raise ValueError("query byte limit")
        return value


class GetArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    catalog_id: Annotated[str, Field(pattern=r"^movie_[0-9]{6}$")]


class Catalog:
    """In-memory copy of the bundled baseline, suitable only for local tests."""

    def __init__(self, records: list[dict] | None = None):
        if records is None:
            raw = files("az_maf_agent").joinpath("data/catalog-v1.json").read_text()
            records = json.loads(raw)["movies"]
        movies = [Movie.model_validate(record) for record in records]
        if not movies or len({movie.id for movie in movies}) != len(movies):
            raise ValueError("invalid catalog baseline")
        self._records = {movie.id: movie for movie in movies}
        self.revision = 0

    def search(self, arguments: object) -> dict:
        try:
            request = SearchArguments.model_validate(arguments)
        except Exception:
            raise Denied("invalid_tool_arguments") from None
        query = request.query.casefold()
        matches = [
            movie
            for movie in self._records.values()
            if query in movie.title.casefold()
            or query in movie.genre.casefold()
            or query in movie.synopsis.casefold()
        ]
        matches.sort(key=lambda movie: (movie.title.casefold(), movie.year, movie.id))
        result = {
            "catalog_version": CATALOG_VERSION,
            "catalog_revision": self.revision,
            "movies": [movie.model_dump(mode="json") for movie in matches[: request.limit]],
            "truncated": len(matches) > request.limit,
        }
        return self._validated_result(result)

    def get(self, arguments: object) -> dict:
        try:
            request = GetArguments.model_validate(arguments)
        except Exception:
            raise Denied("invalid_tool_arguments") from None
        movie = self._records.get(request.catalog_id)
        result = (
            {
                "catalog_version": CATALOG_VERSION,
                "catalog_revision": self.revision,
                "movie": movie.model_dump(mode="json"),
            }
            if movie
            else {
                "catalog_version": CATALOG_VERSION,
                "catalog_revision": self.revision,
                "not_found": True,
                "catalog_id": request.catalog_id,
            }
        )
        return self._validated_result(result)

    def replace(self, catalog_id: object, body: object) -> dict:
        """Replace exactly one existing synthetic record after service authorization."""
        try:
            path = GetArguments.model_validate({"catalog_id": catalog_id})
            movie = Movie.model_validate(body)
        except Exception:
            raise Denied("invalid_catalog_write") from None
        if path.catalog_id != movie.id or movie.id not in self._records:
            raise Denied("catalog_write_denied")
        self._records[movie.id] = movie
        self.revision += 1
        return self.get({"catalog_id": movie.id})

    @staticmethod
    def _validated_result(result: dict) -> dict:
        try:
            # Revalidate after serializing so a future transport cannot inject fields.
            encoded = json.dumps(result, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            if len(encoded) > MAX_RESULT_BYTES:
                raise ValueError("result byte limit")
            if "movies" in result:
                result["movies"] = [
                    Movie.model_validate(movie).model_dump(mode="json")
                    for movie in result["movies"]
                ]
            elif "movie" in result:
                result["movie"] = Movie.model_validate(result["movie"]).model_dump(mode="json")
            elif result.get("not_found") is not True:
                raise ValueError("invalid result")
        except Exception:
            raise Denied("invalid_tool_result") from None
        return result


class MovieDispatcher:
    """Pinned allowlist for the only two Stage 2 read operations."""

    def __init__(self, catalog: Catalog, readers: frozenset[Principal]):
        if not readers:
            raise ValueError("approved readers required")
        self.catalog = catalog
        self.readers = readers
        self.revoked: set[tuple[str, str]] = set()

    def revoke(self, tool_name: str) -> None:
        self.revoked.add((SERVER_ID, tool_name))

    def dispatch(self, principal: Principal, tool_name: object, arguments: object) -> dict:
        if principal not in self.readers:
            raise Denied("tool_permission_denied")
        if not isinstance(tool_name, str) or (SERVER_ID, tool_name) in self.revoked:
            raise Denied("tool_not_allowed")
        if tool_name == "search_movies":
            return self.catalog.search(arguments)
        if tool_name == "get_movie":
            return self.catalog.get(arguments)
        raise Denied("tool_not_allowed")


class CatalogAdminService:
    """A separate service contract; agent/MCP reader identities cannot write."""

    def __init__(self, catalog: Catalog, administrators: frozenset[Principal]):
        if not administrators:
            raise ValueError("catalog administrators required")
        self.catalog = catalog
        self.administrators = administrators

    def put(self, principal: Principal, catalog_id: object, body: object) -> dict:
        if principal not in self.administrators:
            raise Denied("catalog_write_denied")
        return self.catalog.replace(catalog_id, body)
