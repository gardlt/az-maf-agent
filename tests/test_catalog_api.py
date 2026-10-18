import httpx

from az_maf_agent.catalog import Catalog, CatalogAdminService
from az_maf_agent.catalog_api import create_catalog_app
from az_maf_agent.core import LOCAL, Principal


async def test_catalog_put_requires_separate_admin_identity():
    admin = Principal("offline", "catalog-admin", "local-fake")
    catalog = Catalog()
    service = CatalogAdminService(catalog, frozenset({admin}))

    async def agent_identity():
        return LOCAL

    app = create_catalog_app(service, agent_identity)
    original = catalog.get({"catalog_id": "movie_000101"})["movie"]
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="https://catalog"
    ) as client:
        denied = await client.put("/movies/movie_000101", json=original)
        assert denied.status_code == 403
        assert (await client.get("/docs")).status_code == 404
    assert catalog.revision == 0
