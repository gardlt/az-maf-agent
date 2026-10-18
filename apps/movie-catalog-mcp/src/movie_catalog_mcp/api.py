"""Narrow catalog-service HTTP adapter for the Stage 2 admin PUT exercise.

The caller supplies a verified principal through a service-specific
authentication dependency.  This adapter never derives authorization from
request bodies or identity headers and is deliberately separate from the
agent/MCP dispatcher.
"""

from collections.abc import Awaitable, Callable

from fastapi import Depends, FastAPI, HTTPException

from .catalog import CatalogAdminService, Movie
from .contracts import Denied, WorkloadIdentity

Authenticate = Callable[[], Awaitable[WorkloadIdentity]]


def create_catalog_app(service: CatalogAdminService, authenticate: Authenticate) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.exception_handler(Denied)
    async def denied(request, exc):
        return {"error": exc.code}

    @app.put("/movies/{catalog_id}")
    async def replace(catalog_id: str, body: Movie, who=Depends(authenticate)):
        try:
            return service.put(who, catalog_id, body.model_dump(mode="json"))
        except Denied as exc:
            if exc.code == "catalog_write_denied":
                raise HTTPException(403, "catalog_write_denied") from None
            raise HTTPException(422, exc.code) from None

    return app
