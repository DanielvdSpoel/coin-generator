# Phase 8 — Deployment hardening: prod and previews on the UpCloud cluster

Effort: M. The loop works since phase 0; this phase makes prod fit for a public,
CPU-heavy, stateless service and keeps previews cheap.

## Goal

Prod at `coins.danielvdspoel.com` with autoscaling, budgets, rate limits, metrics
and logs in the existing Grafana/Loki, automatic rollback on a failed deploy. PR
previews stay one-replica and bounded by a quota.

## Scope

- Prod umbrella chart values and extra templates: HPA, PDB, ServiceMonitor,
  Traefik rate-limit and body-size Middlewares, NetworkPolicy.
- Workflows finalised: environment protection, rollback, release tags, image
  scanning.
- Observability: `/metrics`, JSON logs, Grafana dashboard, alert rules.
- Abuse controls for public build endpoints.
- Runbook in `deploy/README.md`.

## Out of scope

Multi-region, anything that needs a database. Cloudflare's proxy (orange cloud)
is on: certificates come from DNS-01, and Traefik takes the visitor IP from
Cloudflare's `X-Forwarded-For`, so edge caching, WAF and Cloudflare rate limiting
are available on top of what is listed here.

## Tasks

### 8.1 Images
- [x] Backend: confirm `readOnlyRootFilesystem: true` works with `MPLCONFIGDIR` and
      `/tmp` on emptyDir; `HEALTHCHECK`; record image size.
- [x] Frontend: brotli in nginx if the unprivileged image supports it, else gzip
      only; `client_max_body_size` irrelevant (no proxy in nginx).
- [x] Trivy scan step in `ci.yml`; fail on critical CVEs.

### 8.2 Prod chart (`deploy/prod`)
- [ ] Backend values: `hpa` 2–6 at 60 % CPU (after metrics-server), requests 500m/512Mi, limits 2 CPU/1Gi,
      `env.BUILD_WORKERS: "2"`, `terminationGracePeriodSeconds` > build timeout
      (the chart's `preStop` sleep handles Traefik deregistration).
- [x] Frontend values: 2 replicas, PDB on (chart creates it automatically when
      replicas > 1).
- [x] `templates/servicemonitor.yaml` for the backend `/metrics` (or add a
      `serviceMonitor` knob to `web-service` and bump it; preferred, since the ML
      service will want it too).
- [x] `templates/middleware-ratelimit.yaml`: Traefik `Middleware` with `rateLimit`
      (average 10 rps, burst 20 per source IP) applied to the `/api` router via
      the Ingress annotation
      `traefik.ingress.kubernetes.io/router.middlewares`. Second `Middleware`
      `buffering` with `maxRequestBodyBytes: 10485760` (10 MB, D14).
- [x] `templates/networkpolicy.yaml`: backend ingress only from the Traefik
      namespace; egress limited to DNS, the SMTP host (D19) and filamentcolors.xyz
      (D5).
- [ ] SMTP credentials as a SealedSecret `coin-generator-smtp` in the prod
      namespace (and a logging mailer in previews, `MAILER=log`), referenced via
      the chart's `envFromSecret`.
- [x] Ingress: prod host only, `www` not needed. Keep the preview umbrella
      identical except values, so drift between environments is only numbers.

### 8.3 Workflows
- [x] `ci.yml`: add Trivy, `kubeconform` on rendered charts, E2E on compose
      (phase 7) as a required check.
- [x] `prod.yml`: `environment: production` with a required reviewer if you want a
      manual gate; automatic `helm rollback coin-generator 0` when the post-deploy
      smoke test fails; post a summary to the job.
- [x] `release.yml`: tag `vX.Y.Z` → GitHub Release with generated notes; the
      frontend image gets `version.txt` from the tag or short SHA.
- [ ] Preview cleanup CronJob (in the preview namespace, from the cluster repo):
      delete releases older than 14 days whose PR is closed, in case the
      `closed` event was missed.

### 8.4 Observability
- [x] `prometheus-fastapi-instrumentator` on the backend plus custom metrics:
      build duration histogram by quality, cache hit ratio, build queue depth,
      timeouts, icon trace duration.
- [x] JSON logs to stdout (Alloy → Loki already tails every pod); fields: request
      id, path, status, duration, config hash, cache hit.
- [ ] Grafana dashboard JSON committed under `deploy/grafana/` and applied via the
      cluster repo's dashboard ConfigMap pattern (see `monitoring/unraid/dashboards.yml`).
- [x] `PrometheusRule`: p95 preview build > 2 s for 10 min, 5xx ratio > 2 %,
      backend available replicas < 2, HPA at max for 30 min.
- [ ] Uptime Kuma monitor on `https://coins.danielvdspoel.com/api/health` via the
      existing autokuma ConfigMap.
- [ ] Optional: Rybbit page analytics snippet in the SPA (privacy-friendly,
      self-hosted, already running).

### 8.5 Abuse control (public, D17)
- [x] Traefik rate limit (above) plus a backend per-IP concurrent build cap
      (1 in-flight export, 2 in-flight previews) keyed on `X-Forwarded-For`.
- [x] `max_upload_bytes` 10 MB, `max_icon_vertices` 50 000, `build_timeout_s` 20,
      JSON body limit 2 MB.
- [x] Privacy note in the UI footer: designs are never stored on the server.

### 8.6 Runbook (`deploy/README.md`)
- [x] How previews work, how to regenerate a CI kubeconfig, how to roll back
      prod (`helm history` / `helm rollback`), how to bump the `web-service` chart
      version, where DNS lives, what to do when a certificate does not issue.

## Acceptance criteria

- Opening a PR yields a working preview within ~5 minutes of CI finishing;
  closing it removes the release and certificate.
- Merging to `main` deploys prod with zero downtime (rolling update with
  `maxUnavailable: 0`, PDB).
- A failed prod smoke test rolls back automatically and the job fails visibly.
- Load test: 20 concurrent users dragging sliders keeps p95 GLB latency under 2 s
  with 2 backend pods (record numbers here).
- Backend metrics appear in Grafana; logs are searchable in Loki by config hash.
- Trivy shows no critical CVEs.

## Tests

- `helm template` + `kubeconform` for both charts in CI.
- Smoke tests inside the workflows.
- A short `k6` or `hey` script under `deploy/loadtest/` for the latency number.

## Risks & notes

- Traefik `rateLimit` counts per source IP. The LB uses PROXY protocol and
  Traefik trusts Cloudflare's ranges for forwarded headers (cluster repo, Traefik
  values), so the counted IP is the real visitor for both direct and proxied
  traffic. Re-check when Cloudflare's published ranges change.
- Cloudflare's own rate limiting and WAF rules on `/api/*` are a cheaper first line
  than Traefik middleware; consider them before tuning `rateLimit`.
- Previews and prod share nodes; the preview `ResourceQuota` is the guard.
- `BUILD_WORKERS` × pod CPU limit must stay honest: each build is single-threaded
  Python plus manifold's own threads. Measure before raising.

## Outcome (2026-10-01)

Done in the repo (branch `phase-8-deploy`). Cluster-side steps are listed at
the end.

- **Images:** backend 173 MB (read-only root, `/tmp` emptyDir, `HEALTHCHECK`,
  `MALLOC_ARENA_MAX=2`). Frontend 22 MB on `nginx-unprivileged:1.30-alpine`;
  the old 1.27 base had 2 critical and 40 high CVEs, the new one has none
  fixable. gzip only (no brotli module; Cloudflare compresses anyway).
  Trivy runs in CI and fails on fixable CRITICALs.
- **Chart** (prod and preview share templates): `/api` gets its own Ingress
  carrying the Traefik `rateLimit` (10/s, burst 20, visitor found by skipping
  Cloudflare ranges in XFF) and `buffering` (10 MB) Middlewares. NetworkPolicy
  limits ingress to Traefik (+ monitoring for the API). There are templates
  for ServiceMonitor and PrometheusRule (p95 GLB > 2 s, 5xx > 2 %, build
  timeouts, API replicas < 2, HPA at max when enabled). SMTP comes from
  optional `secretKeyRef`s, so a missing Secret never blocks a deploy.
  Previews keep the CRD extras off. Requests stay at 250m/384Mi and there is
  no HPA while the cluster lacks metrics-server and CPU headroom.
- **Differs from plan:** a ServiceMonitor template in the umbrella chart
  instead of a `serviceMonitor` knob in `web-service` (that needs a release of
  the shared chart). There is no `MAILER` setting: without `SMTP_HOST` the
  logging mailer is used. Preview cleanup deletes releases not deployed for
  14 days, whatever their PR's state, so it needs no GitHub token. The
  per-client preview cap is 3, not 2: the browser abandons superseded GLB
  requests, but the server finishes them.
- **Observability:** `/metrics` (HTTP + build seconds by quality, timeouts,
  builds in flight, mesh/GLB cache hits, trace seconds, per-client refusals).
  Access logs carry `config_hash` and `cache`. Grafana dashboard generated
  into `deploy/grafana/`.
- **Abuse control:** per-client caps (1 export, 3 previews, 429). The client
  IP is read right-to-left through `TRUSTED_PROXIES`, because Cloudflare
  appends to a client-supplied `X-Forwarded-For` and the leftmost entry can
  be forged.
- **CI:** kubeconform on both rendered charts and the cluster manifests
  (CRDs from the datreeio catalogue), Trivy per image, Playwright E2E. prod
  smoke test also checks the SPA and one real build; job summary with Helm
  history. actionlint is clean.
- **Load test** (`deploy/loadtest/`), one pod-sized container, 20 visitors:
  p95 77 ms, 0 failures, 339 MiB. The first run found two real bugs, both
  fixed: 500s from an earcut triangulation that was not a volume, and a mesh
  cache using ~14× its estimate (would have OOM-killed a full pod).

**Live since 2026-10-01** (Helm revision 3). The deployer CRD RBAC, preview
janitor and Grafana dashboard are applied. Verified in prod:
- Both API pods are scraped (`up = 1`) and the four alert rules are loaded.
- `/metrics` is not reachable through the Ingress.
- The Traefik limit passes 21 of a 40-request burst to `/api` and leaves the
  SPA alone.
- Three concurrent exports from one visitor over two pods give one 429.
- GLBs are served gzip-encoded through Cloudflare.

Still open, needing the cluster repo or input:

1. The autokuma entry (snippet in `deploy/README.md`).
2. SMTP credentials sealed as `coin-generator-smtp` (commands in the README).
3. metrics-server, then `hpa.enabled: true`.
4. Required status checks on `main` (branch protection) including the E2E job.
5. Warm previews at the pod level: GLBs are cached per pod, so a slider drag
   that alternates pods builds twice. If it matters, Traefik sticky sessions
   on the API service would fix it.
