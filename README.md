# Coin Designer

Design a two-sided relief challenge coin in the browser and download a print-ready
STL or 3MF. Vue 3 + TresJS frontend, FastAPI + shapely/trimesh backend, no accounts,
no database.

- Plan and decisions: [`docs/plan/`](docs/plan/README.md)
- Product context: [`PRODUCT.md`](PRODUCT.md)
- Engine background: [`docs/reference/`](docs/reference/)
- Deployment: [`deploy/README.md`](deploy/README.md)

## Develop

Requirements: Docker, or locally Python 3.12 + [uv](https://docs.astral.sh/uv/) and Node 22+.

```bash
make install     # backend uv sync + frontend npm ci
make dev         # docker compose: backend :8000 (reload) + frontend :5173
make test        # pytest + vitest
make lint        # ruff + oxlint/eslint/prettier + vue-tsc
make helm-lint   # render both Helm charts
make help        # everything else
```

Without Docker: `make dev-backend` and `make dev-frontend` in two terminals. The
Vite dev server proxies `/api` to the backend, the same way the Ingress does in
preview and prod.

## Engine CLI

The geometry engine runs without the API. Paths are relative to `backend/`; use
`default` instead of a file for the built-in starting design.

```bash
cd backend
uv run python -m src.cli build data/my.coin.json out.stl   # also .glb, .3mf, .zip (STL pair)
uv run python -m src.cli validate default                  # printability warnings
uv run python -m src.cli svg default --face back > back.svg
uv run python -m src.cli bench default                     # build timings per quality
```

`make filaments-snapshot` refreshes the committed filamentcolors.xyz snapshot.

Every pull request gets a preview environment at `pr-<n>.coins.danielvdspoel.com`; see [`deploy/README.md`](deploy/README.md).
