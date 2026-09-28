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
- [ ] Backend: confirm `readOnlyRootFilesystem: true` works with `MPLCONFIGDIR` and
      `/tmp` on emptyDir; `HEALTHCHECK`; record image size.
- [ ] Frontend: brotli in nginx if the unprivileged image supports it, else gzip
      only; `client_max_body_size` irrelevant (no proxy in nginx).
- [ ] Trivy scan step in `ci.yml`; fail on critical CVEs.

### 8.2 Prod chart (`deploy/prod`)
- [ ] Backend values: `hpa` 2–6 at 60 % CPU, requests 500m/512Mi, limits 2 CPU/1Gi,
      `env.BUILD_WORKERS: "2"`, `terminationGracePeriodSeconds` > build timeout
      (the chart's `preStop` sleep handles Traefik deregistration).
- [ ] Frontend values: 2 replicas, PDB on (chart creates it automatically when
      replicas > 1).
- [ ] `templates/servicemonitor.yaml` for the backend `/metrics` (or add a
      `serviceMonitor` knob to `web-service` and bump it; preferred, since the ML
      service will want it too).
- [ ] `templates/middleware-ratelimit.yaml`: Traefik `Middleware` with `rateLimit`
      (average 10 rps, burst 20 per source IP) applied to the `/api` router via
      the Ingress annotation
      `traefik.ingress.kubernetes.io/router.middlewares`. Second `Middleware`
      `buffering` with `maxRequestBodyBytes: 10485760` (10 MB, D14).
- [ ] `templates/networkpolicy.yaml`: backend ingress only from the Traefik
      namespace; egress limited to DNS, the SMTP host (D19) and filamentcolors.xyz
      (D5).
- [ ] SMTP credentials as a SealedSecret `coin-generator-smtp` in the prod
      namespace (and a logging mailer in previews, `MAILER=log`), referenced via
      the chart's `envFromSecret`.
- [ ] Ingress: prod host only, `www` not needed. Keep the preview umbrella
      identical except values, so drift between environments is only numbers.

### 8.3 Workflows
- [ ] `ci.yml`: add Trivy, `kubeconform` on rendered charts, E2E on compose
      (phase 7) as a required check.
- [ ] `prod.yml`: `environment: production` with a required reviewer if you want a
      manual gate; automatic `helm rollback coin-generator 0` when the post-deploy
      smoke test fails; post a summary to the job.
- [ ] `release.yml`: tag `vX.Y.Z` → GitHub Release with generated notes; the
      frontend image gets `version.txt` from the tag or short SHA.
- [ ] Preview cleanup CronJob (in the preview namespace, from the cluster repo):
      delete releases older than 14 days whose PR is closed, in case the
      `closed` event was missed.

### 8.4 Observability
- [ ] `prometheus-fastapi-instrumentator` on the backend plus custom metrics:
      build duration histogram by quality, cache hit ratio, build queue depth,
      timeouts, icon trace duration.
- [ ] JSON logs to stdout (Alloy → Loki already tails every pod); fields: request
      id, path, status, duration, config hash, cache hit.
- [ ] Grafana dashboard JSON committed under `deploy/grafana/` and applied via the
      cluster repo's dashboard ConfigMap pattern (see `monitoring/unraid/dashboards.yml`).
- [ ] `PrometheusRule`: p95 preview build > 2 s for 10 min, 5xx ratio > 2 %,
      backend available replicas < 2, HPA at max for 30 min.
- [ ] Uptime Kuma monitor on `https://coins.danielvdspoel.com/api/health` via the
      existing autokuma ConfigMap.
- [ ] Optional: Rybbit page analytics snippet in the SPA (privacy-friendly,
      self-hosted, already running).

### 8.5 Abuse control (public, D17)
- [ ] Traefik rate limit (above) plus a backend per-IP concurrent build cap
      (1 in-flight export, 2 in-flight previews) keyed on `X-Forwarded-For`.
- [ ] `max_upload_bytes` 10 MB, `max_icon_vertices` 50 000, `build_timeout_s` 20,
      JSON body limit 2 MB.
- [ ] Privacy note in the UI footer: designs are never stored on the server.

### 8.6 Runbook (`deploy/README.md`)
- [ ] How previews work, how to regenerate a CI kubeconfig, how to roll back
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
