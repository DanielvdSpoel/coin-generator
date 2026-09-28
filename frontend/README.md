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
