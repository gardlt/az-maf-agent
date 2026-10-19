"""Pinned, read-only FastMCP client for TMDB movie data."""

import json
import os
import sys
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

import httpx2
from azure.identity.aio import ManagedIdentityCredential
from fastmcp import Client
from fastmcp.client.transports import StdioTransport, StreamableHttpTransport
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, ValidationError

from .model import Denied

CONTRACT = {
    "search_movies": {
        "additionalProperties": False,
        "properties": {"query": {"type": "string"}, "limit": {"default": 5, "type": "integer"}},
        "required": ["query"],
        "type": "object",
    },
    "get_movie": {
        "additionalProperties": False,
        "properties": {"catalog_id": {"type": "string"}},
        "required": ["catalog_id"],
        "type": "object",
    },
}
MAX_RESULT_BYTES = 8192


class Movie(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(pattern=r"^tmdb_[1-9][0-9]{0,9}$")
    title: str = Field(min_length=1, max_length=200)
    year: int | None = Field(ge=1888, le=2100)
    synopsis: str = Field(max_length=1000)
    tmdb_rating: StrictFloat = Field(ge=0, le=10)
    source: Literal["TMDB"]


class SearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    catalog_version: Literal["tmdb-v1"]
    movies: list[Movie] = Field(max_length=10)
    truncated: bool


class GetResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    catalog_version: Literal["tmdb-v1"]
    movie: Movie | None = None
    not_found: bool | None = None
    catalog_id: str | None = Field(default=None, pattern=r"^tmdb_[1-9][0-9]{0,9}$")


def validate_arguments(name: str, arguments: object) -> dict:
    if name not in CONTRACT or not isinstance(arguments, dict):
        raise Denied("tool_not_allowed")
    if name == "search_movies":
        if set(arguments) - {"query", "limit"} or "query" not in arguments:
            raise Denied("invalid_tool_arguments")
        query, limit = arguments["query"], arguments.get("limit", 5)
        if (
            not isinstance(query, str)
            or not 1 <= len(query.strip()) <= 120
            or len(query.encode("utf-8")) > 480
            or type(limit) is not int
            or not 1 <= limit <= 10
        ):
            raise Denied("invalid_tool_arguments")
        return {"query": query.strip(), "limit": limit}
    if set(arguments) != {"catalog_id"}:
        raise Denied("invalid_tool_arguments")
    catalog_id = arguments["catalog_id"]
    if (
        not isinstance(catalog_id, str)
        or not catalog_id.startswith("tmdb_")
        or not catalog_id[5:].isascii()
        or not catalog_id[5:].isdigit()
        or not 1 <= len(catalog_id[5:]) <= 10
        or catalog_id[5] == "0"
        or int(catalog_id[5:]) > 2_147_483_647
    ):
        raise Denied("invalid_tool_arguments")
    return {"catalog_id": catalog_id}


def validate_result(name: str, value: object) -> dict:
    try:
        if not isinstance(value, dict):
            raise ValueError("not an object")
        if len(json.dumps(value, ensure_ascii=False).encode("utf-8")) > MAX_RESULT_BYTES:
            raise ValueError("too large")
        if name == "search_movies":
            return SearchResult.model_validate(value).model_dump(exclude_none=True)
        result = GetResult.model_validate(value)
        if (result.movie is None) == (result.not_found is not True):
            raise ValueError("ambiguous lookup")
        if result.movie is None and result.catalog_id is None:
            raise ValueError("missing id")
        return result.model_dump(exclude_none=True)
    except (ValueError, TypeError, ValidationError):
        raise Denied("invalid_tool_result") from None


class MovieMCPClient:
    """Calls local stdio or the pinned internal MCP host with workload identity."""

    def __init__(self, transport=None, endpoint=None, audience=None, identity_client_id=None):
        self.endpoint = endpoint
        self.audience = None
        self.credential = None
        if endpoint is not None:
            url = urlsplit(endpoint)
            if (
                url.scheme != "https"
                or not url.hostname
                or ".internal." not in url.hostname
                or not url.hostname.endswith(".azurecontainerapps.io")
                or url.path != "/mcp"
                or url.port not in (None, 443)
                or url.username
                or url.password
                or url.query
                or url.fragment
            ):
                raise ValueError("expected pinned internal Container Apps MCP endpoint")
            self.audience = str(UUID(audience))
            self.credential = ManagedIdentityCredential(client_id=identity_client_id or None)
        self.transport = transport or (
            None
            if endpoint is not None
            else StdioTransport(
                sys.executable,
                ["-m", "movie_catalog_mcp.server"],
                env={"TMDB_API_READ_ACCESS_TOKEN": os.environ["TMDB_API_READ_ACCESS_TOKEN"]}
                if os.environ.get("TMDB_API_READ_ACCESS_TOKEN")
                else {},
            )
        )
        self.revoked: set[str] = set()

    def revoke(self, name: str) -> None:
        self.revoked.add(name)

    async def close(self) -> None:
        if self.transport is not None:
            await self.transport.disconnect()
        if self.credential is not None:
            await self.credential.close()

    @staticmethod
    def _no_redirect_client(**kwargs):
        kwargs["follow_redirects"] = False
        return httpx2.AsyncClient(**kwargs)

    async def read(self, name: str, arguments: object) -> dict:
        args = validate_arguments(name, arguments)
        if name in self.revoked:
            raise Denied("tool_not_allowed")
        try:
            transport = self.transport
            if self.endpoint is not None:
                token = await self.credential.get_token(f"api://{self.audience}/.default")
                transport = StreamableHttpTransport(
                    self.endpoint,
                    auth=token.token,
                    httpx_client_factory=self._no_redirect_client,
                )
            async with Client(transport) as client:
                advertised = {tool.name: tool.input_schema for tool in await client.list_tools()}
                if advertised != CONTRACT:
                    raise Denied("tool_contract_drift")
                result = await client.call_tool(name, args)
                if result.is_error:
                    raise Denied("tool_service_error")
                validated = validate_result(name, result.structured_content)
                if name == "get_movie":
                    returned_id = (
                        validated.get("movie", {}).get("id")
                        if "movie" in validated
                        else validated.get("catalog_id")
                    )
                    if returned_id != args["catalog_id"]:
                        raise Denied("invalid_tool_result")
                elif len(validated["movies"]) > args["limit"]:
                    raise Denied("invalid_tool_result")
                return validated
        except Denied:
            raise
        except Exception:
            raise Denied("tool_service_unavailable") from None
