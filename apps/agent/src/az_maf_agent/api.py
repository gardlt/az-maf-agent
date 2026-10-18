"""Minimal hosted boundary. Identity headers and request-body identity are never trusted."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from uuid import UUID

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .config import load_settings
from .core import Principal, Service
from .model import AzureTransport, Denied


class EntraVerifier:
    def __init__(self, tenant: str, audience: str, allowed_users: set[str], key_provider=None):
        self.tenant = str(UUID(tenant))
        if not audience or not allowed_users:
            raise ValueError("audience and approved users are required")
        self.audience, self.allowed_users = audience, frozenset(str(UUID(x)) for x in allowed_users)
        self.issuer = f"https://login.microsoftonline.com/{self.tenant}/v2.0"
        self.keys = key_provider or jwt.PyJWKClient(
            f"https://login.microsoftonline.com/{self.tenant}/discovery/v2.0/keys",
            timeout=5,
            cache_keys=True,
            max_cached_keys=16,
        )

    def authenticate(self, token: str) -> Principal:
        try:
            key = self.keys.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "nbf", "tid", "oid", "sub"]},
            )
            if claims["tid"] != self.tenant:
                raise ValueError("tenant")
            user = str(UUID(claims["oid"]))
        except Exception:
            raise HTTPException(
                401, "invalid_token", headers={"WWW-Authenticate": "Bearer"}
            ) from None
        scopes = claims.get("scp", "")
        if (
            user not in self.allowed_users
            or not isinstance(scopes, str)
            or "Chat.Access" not in scopes.split()
        ):
            raise HTTPException(403, "permission_denied")
        return Principal(self.tenant, user, "entra")


class ChatInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str = Field(min_length=1, max_length=16384)
    revision: int = Field(ge=0)


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        data = bytearray()
        try:
            async with asyncio.timeout(5):
                while True:
                    event = await receive()
                    if event["type"] == "http.disconnect":
                        return
                    data.extend(event.get("body", b""))
                    if len(data) > 32768:
                        return await JSONResponse({"error": "body_limit"}, 413)(
                            scope, receive, send
                        )
                    if not event.get("more_body", False):
                        break
        except TimeoutError:
            return await JSONResponse({"error": "body_timeout"}, 408)(scope, receive, send)
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(data), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


def create_app(service: Service, verifier: EntraVerifier):
    @asynccontextmanager
    async def lifespan(app):
        yield
        await service.close()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(BodyLimit)

    async def principal(request: Request):
        header = request.headers.get("authorization", "")
        if not header.startswith("Bearer ") or len(header) > 16384:
            raise HTTPException(401, "bearer_required", headers={"WWW-Authenticate": "Bearer"})
        return await asyncio.to_thread(verifier.authenticate, header[7:])

    @app.exception_handler(RequestValidationError)
    async def invalid_body(request, exc):
        return JSONResponse({"error": "invalid_request"}, 422)

    @app.exception_handler(Denied)
    async def denied(request, exc):
        status = {
            "session_not_found": 404,
            "tool_not_allowed": 403,
            "tool_not_enabled": 403,
            "invalid_tool_arguments": 422,
            "invalid_tool_result": 502,
            "tool_service_unavailable": 502,
            "tool_service_error": 502,
        }.get(exc.code, 409)
        return JSONResponse({"error": exc.code}, status)

    @app.post("/sessions")
    async def create(who=Depends(principal)):
        return service.create(who)

    @app.post("/sessions/{sid}/chat")
    async def chat(sid: str, body: ChatInput, who=Depends(principal)):
        try:
            return await service.chat(who, sid, body.text, body.revision)
        except asyncio.CancelledError:
            return JSONResponse({"error": "run_cancelled"}, 409)

    @app.post("/sessions/{sid}/reset")
    async def reset(sid: str, who=Depends(principal)):
        return service.reset(who, sid)

    @app.post("/sessions/{sid}/cancel")
    async def cancel(sid: str, who=Depends(principal)):
        return service.cancel(who, sid)

    @app.post("/sessions/{sid}/movies/{tool_name}")
    async def movie_read(sid: str, tool_name: str, body: dict, who=Depends(principal)):
        try:
            return await service.movie_read(who, sid, tool_name, body)
        except asyncio.CancelledError:
            return JSONResponse({"error": "run_cancelled"}, 409)

    return app


def from_env():
    logging.getLogger("agent_framework").setLevel(logging.CRITICAL)
    logging.getLogger("azure").setLevel(logging.CRITICAL)
    settings = load_settings(os.environ["AGENT_CONFIG"])
    movie_model_tools = os.environ.get("ENABLE_MOVIE_MODEL_TOOLS") == "true"
    if movie_model_tools and settings.mode != "azure":
        raise ValueError("model-selected movie tools require live model mode")
    verifier = EntraVerifier(
        os.environ["ENTRA_TENANT_ID"],
        os.environ["ENTRA_AUDIENCE"],
        set(os.environ["ENTRA_ALLOWED_USERS"].split(",")),
    )
    movie_client = None
    if os.environ.get("ENABLE_MOVIE_MCP") == "true":
        from .movie_mcp import MovieMCPClient

        movie_client = MovieMCPClient(
            endpoint=os.environ["MCP_ENDPOINT"], audience=os.environ["MCP_AUDIENCE"]
        )
    service = Service(
        settings,
        AzureTransport(settings) if settings.mode == "azure" else None,
        movie_client=movie_client,
        movie_model_tools=movie_model_tools,
    )
    return create_app(service, verifier)
