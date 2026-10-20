FROM python:3.12.15-slim-trixie@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1 AS build
COPY --from=ghcr.io/astral-sh/uv:0.9.2@sha256:0178fbb205ada6c94ddbd45828f770a2d607cfa7c090276c69b8468a983da557 /uv /uvx /bin/
WORKDIR /build
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
COPY pyproject.toml uv.lock ./
COPY apps/agent/pyproject.toml ./apps/agent/pyproject.toml
COPY apps/movie-catalog-mcp/pyproject.toml ./apps/movie-catalog-mcp/pyproject.toml
RUN uv sync --frozen --no-dev --package az-maf-agent --no-install-package az-maf-agent
COPY apps/agent/src ./apps/agent/src
COPY config ./config
COPY skills ./skills
RUN uv sync --frozen --no-dev --package az-maf-agent

FROM python:3.12.15-slim-trixie@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
WORKDIR /app
RUN useradd --uid 10001 --create-home appuser
COPY --from=build --chown=10001:10001 /app/.venv /app/.venv
COPY --from=build --chown=10001:10001 /build/apps/agent/src /app/src
COPY --from=build --chown=10001:10001 /build/config /app/config
COPY --from=build /build/skills /app/skills
ENV PATH=/app/.venv/bin:$PATH PYTHONPATH=/app/src PYTHONUNBUFFERED=1
USER 10001
EXPOSE 8000
CMD ["uvicorn", "az_maf_agent.api:from_env", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--limit-concurrency", "32", "--no-access-log"]
