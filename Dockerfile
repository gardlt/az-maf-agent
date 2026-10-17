FROM python:3.12.12-slim@sha256:5a2c2a6e9a7bbce0f6bb4b8717cb7df991e7cc2cbbff3f4cf43435ba2a88bba2 AS build
COPY --from=ghcr.io/astral-sh/uv:0.9.2@sha256:25a952c8c8154503a0980a9f38f995340ba20d14ccaa2dcf2e56a455ff5a3268 /uv /uvx /bin/
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY config ./config
RUN uv sync --frozen --no-dev

FROM python:3.12.12-slim@sha256:5a2c2a6e9a7bbce0f6bb4b8717cb7df991e7cc2cbbff3f4cf43435ba2a88bba2
WORKDIR /app
RUN useradd --uid 10001 --create-home appuser
COPY --from=build --chown=10001:10001 /build/.venv /app/.venv
COPY --from=build --chown=10001:10001 /build/config /app/config
ENV PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1
USER 10001
EXPOSE 8000
CMD ["uvicorn", "az_maf_agent.api:from_env", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--limit-concurrency", "32", "--no-access-log"]
