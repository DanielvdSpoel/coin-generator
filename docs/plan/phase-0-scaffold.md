# Phase 0 — Scaffold, tooling, CI, preview-env skeleton

Effort: S–M

## Goal

An empty but fully wired monorepo: both apps start with one command, lint and tests
run locally and in GitHub Actions, images build, and a PR gets a preview URL even if
the page is only "hello". Getting the deploy loop working on nothing is far cheaper
than on a finished app, and the whole loop already exists in mailbunny to copy from.

## Scope

- Repo layout from `01-architecture.md`.
- Backend skeleton: `create_app()`, `/api/healthz`, settings, container with no
  providers yet, pytest with one test.
- Frontend skeleton: Vite + Vue 3 + TS + Pinia + Tailwind v4 + shadcn-vue + vitest
  + eslint + prettier, one view showing the backend health.
- `compose.yaml` for local dev, `Makefile`.
- Dockerfiles for both apps.
- Helm umbrella charts `deploy/preview` and `deploy/prod` on `web-service`.
- GitHub Actions `ci.yml`, `preview.yml`, `prod.yml` in their first form.
- Cluster prerequisites: two namespaces, two CI kubeconfigs, wildcard DNS.

## Out of scope

Anything that depends on the engine. Hardening (phase 8).

## Tasks

### 0.1 Repo
- [x] `git init`, `.gitignore` (include `*secret.y*ml` and `ci-kubeconfig.yaml` like
      the cluster repo), `.editorconfig`, move the four source docs into
      `docs/reference/`.
- [x] `Makefile`: `dev`, `test`, `lint`, `types` (placeholder), `images`,
      `helm-lint`.

### 0.2 Backend
- [x] `uv init`, pin Python 3.12, runtime + dev deps, `ruff` config, `pytest`
      config, `src/main.py` with the app factory guarded like MRA
      (`PYTEST_VERSION` check), `src/settings.py`, `src/container.py`,
      `api/health/router.py` (`/api/healthz`, `/api/health`).
- [x] Dockerfile: multi-stage, `python:3.12-slim` + `libcairo2`, `uv sync
      --frozen`, non-root user 10001 (matches the `web-service` FastAPI example),
      fonts and data copied in, `uvicorn src.main:app --host 0.0.0.0 --port 8000
      --workers 1`. One worker per pod; scale with replicas so the cache and build
      pool stay predictable. `MPLCONFIGDIR=/tmp/mpl` for a read-only root later.

### 0.3 Frontend
- [x] `npm create vite@latest` (vue-ts), Node 22. Add Pinia, vue-router, Tailwind v4
      (`@tailwindcss/vite`), then `npx shadcn-vue@latest init` (Tailwind v4, TS,
      `components/ui/` alias). Add `button`, `card` to prove the pipeline.
- [x] vitest, `@vue/test-utils`, eslint (+ oxlint as in mailbunny), prettier,
      `npm run type-check`.
- [x] `services/utils/Fetcher.ts`, `stores/health.ts`, one view calling
      `/api/health`. `VITE_API_URL=/api` baked in; Vite dev server proxies `/api`.
- [x] Dockerfile: build stage → `nginxinc/nginx-unprivileged` on 8080, `nginx.conf`
      with history fallback, `/health` returning 200, gzip, immutable cache headers
      for hashed assets, `no-cache` for `index.html`. No `/api` proxy in nginx; the
      Ingress does path routing. Writable dirs on emptyDir so the root FS can be
      read-only.

### 0.4 Local dev
- [x] `compose.yaml`: backend with `--reload` and a bind mount, frontend Vite dev
      server. `make dev` = `docker compose up`.

### 0.5 Helm charts (`deploy/`)
- [x] Copy `deploy/generate-ci-kubeconfig.sh` from mailbunny; parameterised by
      `NS` already. Document running it twice (`NS=coin-generator-preview`,
      `NS=coin-generator`) and uploading as `KUBECONFIG_PREVIEW` /
      `KUBECONFIG_PROD`.
- [x] `deploy/preview/Chart.yaml`: dependencies `web-service` (alias `backend`) and
      `web-service` (alias `frontend`) from `oci://ghcr.io/danielvdspoel/charts`,
      pinned version. `Chart.lock` committed, `charts/` gitignored (CI runs `helm
      dependency build`).
- [x] `deploy/preview/values.yaml`: `host` required; backend `port: 8000`, probes on
      `/api/healthz` and `/api/health`, `env: { ENVIRONMENT: preview,
      BUILD_WORKERS: "1" }`, requests 250m/512Mi, limits 1 CPU/1Gi, 1 replica, no
      HPA/PDB, `ingress.enabled: false`; frontend as in mailbunny's `frontend:`
      block (nginx-unprivileged, read-only FS, `/health` probes), `ingress.enabled:
      false`.
- [x] `deploy/preview/templates/ingress.yaml`: one host, `/api` → backend Service,
      `/` → frontend Service, cert-manager annotation, `fail` when `host` is empty.
      `_helpers.tpl` for service names.
- [x] `deploy/prod/`: same structure; `host: coins.danielvdspoel.com`, backend
      `hpa: { enabled: true, minReplicas: 2, maxReplicas: 6, cpuTargetPercent: 60
      }`, frontend `replicas: 2`, PDBs on. Extra templates added in phase 8.
- [x] `helm lint` + `helm template` both charts locally.

### 0.6 Cluster prerequisites (one-time, by hand, documented in `deploy/README.md`)
- [x] `deploy/cluster/namespaces.yml` and `preview-wildcard-certificate.yml`
      (namespaces, shared `*.coins` certificate via `letsencrypt-dns01`); confirm
      `ghcr-secret` was reflected into both.
- [ ] Run the kubeconfig script for both namespaces; `gh secret set`.
- [x] Cloudflare: `coins.danielvdspoel.com` (orange, Full strict) and
      `*.coins.danielvdspoel.com` (grey: Universal SSL does not cover second-level
      names) → Traefik LB.
- [ ] Repo variable `PREVIEW_DOMAIN=coins.danielvdspoel.com`.
- [ ] Optional: `ResourceQuota` in the preview namespace so many open PRs cannot
      starve prod; add it to `../upcloud-cluster/apps/coin-generator/` alongside
      the namespace manifests so the cluster repo stays the source of truth for
      cluster-level objects.

### 0.7 Workflows (`.github/workflows/`)
- [x] `ci.yml` (from mailbunny, adapted): backend ruff + pytest, frontend oxlint +
      eslint + prettier + type-check + vitest + `vite build`, `helm lint` +
      `helm template` for `deploy/preview` and `deploy/prod`. Concurrency group
      per ref, cancel in progress.
- [x] `preview.yml`: copy mailbunny's verbatim, then adapt: image names, no
      Postgres/Redis `--set`s, `HOST=pr-<n>.${PREVIEW_DOMAIN}`, health check on
      `https://$HOST/api/health`, `KUBECONFIG_PREVIEW` secret, namespace
      `coin-generator-preview`. Keep the stuck-release recovery step and the
      teardown job (uninstall + delete `pr-<n>-tls` secret and certificate).
- [x] `prod.yml`: on push to `main`: build + push images tagged `sha-<sha>` and
      `latest`; job `deploy` with `environment: production`, `KUBECONFIG_PROD`,
      `helm upgrade --install coin-generator deploy/prod --set
      backend.image.tag=sha-… --set frontend.image.tag=sha-… --wait`, smoke test
      `https://coins.danielvdspoel.com/api/health`, `helm rollback` on failure.

## Status

Scaffold implemented 2026-09-28. Open items are the one-time cluster steps in 0.6 and
the first real PR to prove the preview loop. shadcn-vue's defaults pulled the Geist
font from Google Fonts into `src/assets/main.css`; phase 3 (or `/impeccable shape`)
decides the real typography and should replace that import.

## Acceptance criteria

- `make dev` brings up both apps; the frontend shows backend health.
- `make test`, `make lint`, `make helm-lint` pass on a clean clone.
- A PR gets a sticky comment with `https://pr-<n>.coins.danielvdspoel.com` that
  serves the SPA and `/api/health` over valid TLS.
- Closing the PR removes the release and its certificate.
- Merging to `main` updates `https://coins.danielvdspoel.com`.

## Tests

- Backend: `test_healthz` and `test_health` via `TestClient`.
- Frontend: one vitest for the health store with a mocked `Fetcher`.
- CI: `helm template` output validated with `kubeconform` (as in
  `opinionated-charts`).

## Risks & notes

- The `web-service` chart pins `imagePullSecrets: ghcr-secret` by default and
  honours the image's `USER`; keep the backend image's user at 10001 so no
  `runAsUser` override is needed.
- Certificates come from the `letsencrypt-dns01` ClusterIssuer (Cloudflare API,
  set up in the cluster repo on 2026-09-28). Previews share one wildcard
  certificate, so nothing is issued or deleted per PR.
- If `web-service` needs a knob we lack (e.g. a ServiceMonitor), add it to
  `opinionated-charts` and bump the version rather than templating around it in
  the umbrella.
