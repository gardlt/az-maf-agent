"""Minimal hosted boundary. Identity headers and request-body identity are never trusted."""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from uuid import UUID

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .approval_ledger import ApprovalLedger, CreditArguments
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
    skill_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9-]{0,63}$")
    skill_version: str | None = Field(default=None, pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")


class MemorySaveInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    category: str = Field(min_length=1, max_length=32)
    value: str = Field(min_length=1, max_length=32)
    consent: bool
    expected_generation: int = Field(ge=0)


class MemoryCorrectInput(MemorySaveInput):
    expected_revision: int = Field(ge=1)


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
        if service.safety is not None:
            from .control_telemetry import fault_signal

            fault_signal(exc.code)
        status = {
            "global_stop": 503,
            "control_unavailable": 503,
            "control_invalid": 503,
            "control_state_missing": 503,
            "control_rollback": 503,
            "control_timeout": 503,
            "audit_unavailable": 503,
            "capability_disabled": 403,
            "action_forbidden": 403,
            "approval_required": 403,
            "approval_invalid": 403,
            "control_not_enabled": 403,
            "run_not_found": 404,
            "receipt_not_found": 404,
            "shared_concurrency": 429,
            "shared_daily_budget": 429,
            "shared_run_budget": 429,
            "shared_tool_budget": 429,
            "shared_memory_budget": 429,
            "session_capacity": 429,
            "control_capacity": 429,
            "control_backpressure": 429,
            "session_not_found": 404,
            "memory_not_found": 404,
            "memory_forbidden": 403,
            "memory_not_enabled": 403,
            "memory_consent_required": 403,
            "memory_invalid": 422,
            "tool_not_allowed": 403,
            "tool_not_enabled": 403,
            "invalid_tool_arguments": 422,
            "invalid_tool_result": 502,
            "tool_service_unavailable": 502,
            "tool_service_error": 502,
        }.get(exc.code, 409)
        return JSONResponse({"error": exc.code}, status)

    @app.get("/about", response_class=HTMLResponse)
    async def about(who=Depends(principal)):
        return HTMLResponse(
            "<!doctype html><html lang='en'><meta charset='utf-8'>"
            "<title>Agent Bones credits</title>"
            "<h1>Agent Bones</h1><h2>Movie data credits</h2>"
            "<p>Movie search and details are provided by "
            "<a href='https://www.themoviedb.org'>TMDB</a>.</p>"
            "<img width='80' alt='TMDB approved primary logo' "
            "src='https://www.themoviedb.org/assets/2/v4/logos/v2/"
            "blue_square_2-d537fb228cf3ded904ef09b136fe3fec72548ebc1fea3fbbd1ad9e36364db38b.svg'>"
            "<p>This product uses the TMDB API but is not endorsed or certified by TMDB.</p>"
            "</html>",
            headers={
                "Content-Security-Policy": "default-src 'none'; img-src https://www.themoviedb.org"
            },
        )

    @app.post("/sessions")
    async def create(who=Depends(principal)):
        return await service.create_async(who)

    @app.get("/sessions/{sid}")
    async def session_status(sid: str, who=Depends(principal)):
        return await service.session_status(who, sid)

    @app.post("/sessions/{sid}/chat")
    async def chat(sid: str, body: ChatInput, who=Depends(principal)):
        try:
            return await service.chat(
                who,
                sid,
                body.text,
                body.revision,
                skill_id=body.skill_id,
                skill_version=body.skill_version,
            )
        except asyncio.CancelledError:
            return JSONResponse({"error": "run_cancelled"}, 409)

    @app.post("/sessions/{sid}/reset")
    async def reset(sid: str, who=Depends(principal)):
        return await service.reset_async(who, sid)

    @app.post("/sessions/{sid}/cancel")
    async def cancel(sid: str, who=Depends(principal)):
        return await service.reset_async(who, sid, clear=False)

    @app.post("/sessions/{sid}/movies/{tool_name}")
    async def movie_read(sid: str, tool_name: str, body: dict, who=Depends(principal)):
        try:
            return await service.movie_read(who, sid, tool_name, body)
        except asyncio.CancelledError:
            return JSONResponse({"error": "run_cancelled"}, 409)

    @app.get("/sessions/{sid}/memory")
    async def inspect_memory(sid: str, who=Depends(principal)):
        return await service.memory_async(who, sid, "inspect")

    @app.post("/sessions/{sid}/memory")
    async def save_memory(sid: str, body: MemorySaveInput, who=Depends(principal)):
        return await service.memory_async(
            who,
            sid,
            "save",
            preference={"category": body.category, "value": body.value},
            consent=body.consent,
            expected_generation=body.expected_generation,
        )

    @app.put("/sessions/{sid}/memory/{record_id}")
    async def correct_memory(
        sid: str, record_id: str, body: MemoryCorrectInput, who=Depends(principal)
    ):
        return await service.memory_async(
            who,
            sid,
            "correct",
            record_id=record_id,
            preference={"category": body.category, "value": body.value},
            consent=body.consent,
            expected_generation=body.expected_generation,
            expected_revision=body.expected_revision,
        )

    @app.delete("/sessions/{sid}/memory/{record_id}")
    async def forget_memory(sid: str, record_id: str, who=Depends(principal)):
        return await service.memory_async(who, sid, "forget", record_id=record_id)

    @app.delete("/sessions/{sid}/memory")
    async def forget_all_memory(sid: str, who=Depends(principal)):
        return await service.memory_async(who, sid, "forget_all")

    class SimulationExecute(BaseModel):
        model_config = ConfigDict(extra="forbid", strict=True)
        approval_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
        arguments: CreditArguments

    def require_safety():
        if service.safety is None:
            raise Denied("control_not_enabled")
        return service.safety

    @app.get("/runs/{run_id}")
    async def run_status(run_id: str, who=Depends(principal)):
        safety = require_safety()
        return await safety.call(safety.controls.inspect, who, run_id)

    @app.post("/runs/{run_id}/cancel")
    async def cancel_run(run_id: str, who=Depends(principal)):
        safety = require_safety()
        return await safety.call(safety.controls.cancel, who, run_id)

    @app.post("/simulations/requests")
    async def request_simulation(body: CreditArguments, who=Depends(principal)):
        from uuid import uuid4

        safety = require_safety()
        run_id = str(uuid4())
        admitted = await safety.call(safety.controls.start, who, run_id)
        return await safety.call(
            ApprovalLedger(safety.controls).display,
            who,
            run_id,
            admitted["epoch"],
            body.model_dump(),
        )

    @app.post("/simulations/{run_id}/execute")
    async def execute_simulation(run_id: str, body: SimulationExecute, who=Depends(principal)):
        safety = require_safety()
        run = await safety.call(safety.controls.inspect, who, run_id)
        result = await safety.call(
            ApprovalLedger(safety.controls).execute,
            who,
            run_id,
            run["epoch"],
            body.arguments.model_dump(),
            body.approval_id,
        )
        await safety.call(safety.controls.finish, who, run_id, run["epoch"], "completed")
        return result

    @app.get("/simulations/receipts/{approval_id}")
    async def simulation_receipt(approval_id: str, who=Depends(principal)):
        safety = require_safety()
        return await safety.call(ApprovalLedger(safety.controls).receipt, who, approval_id)

    return app


def from_env():
    logging.getLogger("agent_framework").setLevel(logging.CRITICAL)
    logging.getLogger("azure").setLevel(logging.CRITICAL)
    settings = load_settings(os.environ["AGENT_CONFIG"])
    movie_model_tools = os.environ.get("ENABLE_MOVIE_MODEL_TOOLS", "").lower() == "true"
    if movie_model_tools and settings.mode != "azure":
        raise ValueError("model-selected movie tools require live model mode")
    verifier = EntraVerifier(
        os.environ["ENTRA_TENANT_ID"],
        os.environ["ENTRA_AUDIENCE"],
        set(os.environ["ENTRA_ALLOWED_USERS"].split(",")),
    )
    movie_client = None
    if os.environ.get("ENABLE_MOVIE_MCP", "").lower() == "true":
        from .movie_mcp import MovieMCPClient

        movie_client = MovieMCPClient(
            endpoint=os.environ["MCP_ENDPOINT"],
            audience=os.environ["MCP_AUDIENCE"],
            identity_client_id=os.environ.get("MCP_IDENTITY_CLIENT_ID"),
        )
    skill_registry = None
    skill_permissions = None
    if os.environ.get("SKILL_BUNDLE"):
        from pathlib import Path

        from .skills import READ_TOOLS, reviewed_registry

        # Both paths are operator configuration; no request can select them.
        if os.environ.get("SKILL_CONTROL_RESOURCE_ID"):
            from .skill_control import AzureTagControl

            skill_registry = reviewed_registry(Path(os.environ["SKILL_BUNDLE"]))
            skill_registry.control_reader = AzureTagControl(os.environ["SKILL_CONTROL_RESOURCE_ID"])
        else:
            skill_registry = reviewed_registry(
                Path(os.environ["SKILL_BUNDLE"]), Path(os.environ["SKILL_CONTROL"])
            )
        skill_users = frozenset(os.environ["SKILL_ALLOWED_USERS"].split(","))
        tenant = os.environ["ENTRA_TENANT_ID"]

        def skill_permissions(who):
            return (
                READ_TOOLS
                if who.source == "entra" and who.tenant == tenant and who.user in skill_users
                else frozenset()
            )

    if os.environ.get("ENABLE_MEMORY", "false").lower() == "true" and not movie_model_tools:
        raise ValueError("hosted memory recall requires the governed movie model loop")
    memory_service, memory_permissions = configured_memory(os.environ)
    safety, session_repository = configured_safety(os.environ, settings)
    service = Service(
        settings,
        AzureTransport(settings) if settings.mode == "azure" else None,
        movie_client=movie_client,
        movie_model_tools=movie_model_tools,
        skill_registry=skill_registry,
        skill_permissions=skill_permissions,
        memory_service=memory_service,
        memory_permissions=memory_permissions,
        safety=safety,
        session_repository=session_repository,
    )
    return create_app(service, verifier)


def configured_safety(env, settings):
    enabled = env.get("ENABLE_GUARDRAILS", "false").lower()
    shared = env.get("ENABLE_SHARED_SESSIONS", "false").lower()
    if enabled not in {"true", "false"} or shared not in {"true", "false"}:
        raise ValueError("guardrail/session enable flags must be true or false")
    if enabled == "false":
        if shared == "true":
            raise ValueError("shared sessions require shared controls")
        return None, None
    from .guardrail_blob import BlobControlBackend
    from .guardrails import RunControls
    from .shared_sessions import BlobSessionBackend, SessionRepository
    from .supervisor import SafetySupervisor

    telemetry = None
    if env.get("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        from .control_telemetry import azure_telemetry

        telemetry = azure_telemetry(env["APPLICATIONINSIGHTS_CONNECTION_STRING"])
    safety = SafetySupervisor(
        RunControls(BlobControlBackend(env["CONTROL_ACCOUNT"], telemetry=telemetry), settings)
    )
    repository = (
        SessionRepository(BlobSessionBackend(env["SESSION_ACCOUNT"]), settings)
        if shared == "true"
        else None
    )
    return safety, repository


def configured_memory(env, *, store_factory=None, audit=None):
    """Operator-only configuration: never accept a backend or scope from requests."""
    enabled = env.get("ENABLE_MEMORY", "false").lower()
    if enabled not in {"true", "false"}:
        raise ValueError("ENABLE_MEMORY must be true or false")
    if enabled == "false":
        return None, None
    from .blob_memory import BlobMemoryStore
    from .memory import OPERATIONS, MemoryService, load_memory_policy

    if env.get("MEMORY_BACKEND") != "azure_blob":
        raise ValueError("only the approved azure_blob memory backend is supported")
    tenant = str(UUID(env["ENTRA_TENANT_ID"]))
    users = frozenset(str(UUID(value)) for value in env["MEMORY_ALLOWED_USERS"].split(","))
    admitted_users = frozenset(str(UUID(value)) for value in env["ENTRA_ALLOWED_USERS"].split(","))
    if not users or not users <= admitted_users:
        raise ValueError("memory users must be explicitly admitted API users")
    policy = load_memory_policy(env["MEMORY_POLICY"])
    if policy.scope != "user" or policy.retention_seconds != 2592000:
        raise ValueError("hosted movie preferences require approved user scope and 30-day expiry")
    # Validate all policy and identity configuration before allocating a network client.
    store = (store_factory or BlobMemoryStore)(env["MEMORY_ACCOUNT"], env["MEMORY_CONTAINER"])
    service = MemoryService(
        policy,
        store,
        audit=audit or (lambda event: print(json.dumps(event), flush=True)),
    )

    def permissions(who):
        return (
            OPERATIONS
            if who.source == "entra" and who.tenant == tenant and who.user in users
            else frozenset()
        )

    return service, permissions
