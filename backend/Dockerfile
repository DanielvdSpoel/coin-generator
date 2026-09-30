# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
# cairosvg (phase 5) needs libcairo2; matplotlib/fontTools need nothing extra.
RUN apt-get update && apt-get install -y --no-install-recommends libcairo2 && rm -rf /var/lib/apt/lists/*

FROM base AS deps
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

FROM base AS runtime
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app
WORKDIR /app
COPY --from=deps /app/.venv /app/.venv
COPY src ./src
COPY fonts ./fonts
COPY data ./data
# MALLOC_ARENA_MAX: build threads each grow a glibc arena that is rarely
# returned; two arenas keep RSS close to what the mesh cache actually holds.
ENV PATH="/app/.venv/bin:$PATH" MPLCONFIGDIR=/tmp/mpl ENVIRONMENT=prod MALLOC_ARENA_MAX=2
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/healthz', timeout=2).status == 200 else 1)"
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
