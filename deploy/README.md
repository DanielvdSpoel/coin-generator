# Deployment

Coin Designer runs on the UpCloud Kubernetes cluster described in
`../upcloud-cluster` (Traefik ingress, cert-manager with the `letsencrypt-dns01`
ClusterIssuer, SealedSecrets, the `ghcr-secret` pull secret reflected into every
namespace). Nothing here installs cluster-wide components; `cluster/` only adds
the two namespaces and one shared certificate.

| environment | namespace | host | release | trigger |
|---|---|---|---|---|
| preview | `coin-generator-preview` | `pr-<n>.coins.danielvdspoel.com` | `pr-<n>` | PR opened / updated; removed on close |
| prod | `coin-generator` | `coins.danielvdspoel.com` | `coin-generator` | push to `main` |

Both use the same umbrella chart shape: two `web-service` subcharts
(`oci://ghcr.io/danielvdspoel/charts/web-service`, aliases `backend` and `frontend`)
plus one Ingress that routes `/api` to the backend and `/` to the SPA. `preview/`
and `prod/` differ only in values.

TLS uses DNS-01 (`letsencrypt-dns01`), so both hosts may be proxied by Cloudflare
(orange cloud). Prod gets its own certificate per Ingress; previews share the
wildcard `*.coins.danielvdspoel.com` certificate from
`cluster/preview-wildcard-certificate.yml`, so a new PR has TLS immediately.
Traefik trusts Cloudflare's IP ranges for `X-Forwarded-For`, so per-IP rate limits
and access logs see the real visitor IP either way.

## One-time setup

Prerequisite in the cluster repo: the `letsencrypt-dns01` ClusterIssuer
(`infrastructure/cert-manager/README.md`) must be Ready, and both namespaces
must be in the Reflector allow-list of `infrastructure/ghcr-pull-secret`.

1. Cluster-side manifests, applied by a cluster admin (the CI kubeconfigs are
   namespace-scoped and cannot create namespaces):
   ```bash
   kubectl apply -f deploy/cluster/
   kubectl get secret ghcr-secret -n coin-generator-preview                    # reflected by Reflector
   kubectl -n coin-generator-preview get certificate coins-preview-wildcard -w  # READY True (~1–2 min)
   ```
   - `cluster/namespaces.yml` — `coin-generator` and `coin-generator-preview`.
   - `cluster/preview-wildcard-certificate.yml` — `*.coins.danielvdspoel.com` via
     DNS-01, stored as Secret `coins-preview-wildcard-tls`. Every preview
     Ingress points its `tls.secretName` at it and sets no issuer annotation, so
     a new PR gets TLS instantly and teardown has no certificate to clean up.
     cert-manager renews it; Traefik reloads the Secret without a restart.
   - `cluster/deployer-crd-rbac.yml` — lets the prod CI deployer manage the
     chart's Traefik `Middleware`s, `ServiceMonitor` and `PrometheusRule` (the
     built-in `admin` role does not cover CRDs). **Apply before the first
     deploy that contains them**, or `helm upgrade` is refused.
   - `cluster/preview-cleanup-cronjob.yml` — nightly janitor that uninstalls
     previews not deployed for 14 days (missed `closed` events).
   Prod requests its own certificate through the Ingress annotation
   `cert-manager.io/cluster-issuer: letsencrypt-dns01`.
2. CI credentials, one namespace-admin ServiceAccount per namespace:
   ```bash
   NS=coin-generator-preview ./generate-ci-kubeconfig.sh --set-secret KUBECONFIG_PREVIEW
   NS=coin-generator         ./generate-ci-kubeconfig.sh --set-secret KUBECONFIG_PROD
   ```
3. DNS in Cloudflare (zone `danielvdspoel.com`), done 2026-09-28. Certificates
   come from DNS-01, so the proxy never gets in the way of issuance; whether a
   record can be proxied depends only on Cloudflare's *edge* certificate.

   | type  | name      | content                                               | proxy  |
   |-------|-----------|-------------------------------------------------------|--------|
   | CNAME | `coins`   | `lb-0a5e0816152f4e54a879d0c06547b38f-1.upcloudlb.com` | orange |
   | CNAME | `*.coins` | `lb-0a5e0816152f4e54a879d0c06547b38f-1.upcloudlb.com` | grey   |

   `*.coins` stays **DNS-only (grey)**: Cloudflare's free Universal SSL covers
   `danielvdspoel.com` and `*.danielvdspoel.com` only, so a proxied
   `pr-12.coins.danielvdspoel.com` fails TLS at the edge before reaching Traefik.
   Grey sends previews straight to Traefik, which serves the wildcard certificate.
   Proxying previews would need Cloudflare Advanced Certificate Manager (paid);
   not worth it for ephemeral environments.

   SSL/TLS mode is **Full (strict)**. Traefik trusts Cloudflare's
   `X-Forwarded-For` (see the cluster repo's `infrastructure/traefik/README.md`),
   so rate limits and logs see real visitor IPs for the proxied prod host.
4. Repo variable `PREVIEW_DOMAIN=coins.danielvdspoel.com`.
5. Optional: a `ResourceQuota` in `coin-generator-preview` (add it to
   `cluster/`) so many open PRs cannot starve prod.
6. Observability, applied by a cluster admin:
   ```bash
   kubectl apply --server-side -f deploy/grafana/coin-generator-dashboard.yml
   ```
   The dashboard lands in Grafana's "Apps" folder. It is generated: edit
   `grafana/build_dashboard.py`, run it, commit both files. The
   `ServiceMonitor` and `PrometheusRule` ship with the prod chart. For Uptime
   Kuma, add a key to the `autokuma-monitors` ConfigMap in the cluster repo
   (`monitoring/uptime-kuma/autokuma-monitors-configmap.yml`):
   ```toml
   coin-generator.toml: |
     [http]
     name = "Coin Designer"
     url = "https://coins.danielvdspoel.com/api/health"
     parent_name = "cluster"
     expiry_notification = true
   ```

## Day to day

- Previews: automatic. The sticky PR comment carries the URL and image tags.
- Prod: merge to `main`. The workflow waits for the rollout and smoke-tests
  `/api/health`, the SPA and one real `/api/stats` build; on failure it runs
  `helm rollback` and the job fails. The job summary shows the Helm history.
- Releases: `git tag v1.2.3 && git push --tags` builds images tagged `1.2.3`
  and `1.2` and creates a GitHub Release with generated notes. Deploys still
  come from `main`; pin prod to a release with
  `helm upgrade ... --set backend.image.tag=1.2.3 --set frontend.image.tag=1.2.3`.
- Metrics: Grafana → Apps → Coin Designer (request rate, p95 per endpoint,
  build times, cache hit ratio, timeouts, refused requests, pod CPU/memory).
  Alerts (`CoinPreviewSlow`, `CoinApiErrors`, `CoinBuildTimeouts`,
  `CoinApiReplicasLow`) go through the cluster's Alertmanager.
- Logs: Loki, `{namespace="coin-generator", pod=~".*-api-.*"} | json`. Access
  lines for GLB and export requests carry `config_hash` (the GLB ETag) and
  `cache`; the dashboard's log panel filters by a hash prefix.
- Abuse controls, outermost first: Traefik `rateLimit` on `/api` (10 req/s,
  burst 20 per visitor), `buffering` (10 MB bodies), the backend's
  per-visitor caps (1 export, 3 previews in flight → 429) and contact limit
  (3 per 10 min), then the build timeout (20 s). The visitor is found in
  `X-Forwarded-For` by skipping Cloudflare's ranges (`TRUSTED_PROXIES` in
  `prod/values.yaml` and `apiMiddlewares.rateLimit.trustedProxies`; update both
  when Cloudflare publishes new ranges).
- Load test: `loadtest/README.md` (k6, 20 visitors dragging a slider).
- Manual rollback:
  ```bash
  helm history coin-generator -n coin-generator
  helm rollback coin-generator <revision> -n coin-generator
  ```
- Local check of the charts: `make helm-lint`.
- Bumping the `web-service` chart: change `version` in both `Chart.yaml` files,
  run `helm dependency update deploy/preview deploy/prod`, commit the lock files.
- Certificates: `kubectl get certificate -A | grep coin` shows prod and the preview
  wildcard; cert-manager renews both. If the wildcard is ever deleted, re-apply
  `cluster/preview-wildcard-certificate.yml`; running previews pick up the new
  Secret without a redeploy.
- A certificate that does not issue: `kubectl describe certificate -n <ns>`,
  then the `CertificateRequest`, `Order` and `Challenge` it points to
  (`kubectl get challenges -A`). DNS-01 failures are nearly always the
  Cloudflare API token (SealedSecret in the cluster repo's
  `infrastructure/cert-manager/`) or a stale `_acme-challenge` TXT record;
  delete the failed `Challenge` to retry. Let's Encrypt rate limits show in the
  `Order` status. Meanwhile Traefik serves its default certificate.

## Known gaps

- **Cluster CPU is nearly fully requested** (3 nodes × 2 vCPU, ~90 % of requests
  allocated by other apps on 2026-09-28). The charts use small CPU requests so
  pods schedule; phase 1+ builds will need either a fourth node or right-sizing
  the other apps' requests before raising ours.

- **No metrics-server on the cluster.** The prod backend runs a fixed 2 replicas;
  `hpa.enabled` stays false until metrics-server is installed from the cluster
  repo. The `CoinApiAtMaxReplicas` alert appears once it is enabled.
- **Egress is not restricted.** The NetworkPolicies limit ingress to Traefik
  (and Prometheus for the API). Pinning egress to DNS, the SMTP host and
  filamentcolors.xyz needs a CiliumNetworkPolicy with `toFQDNs`.
- **Frontend compression is gzip only**: the unprivileged nginx image has no
  brotli module, and Cloudflare re-compresses for browsers anyway.
- **Images must declare a numeric `USER`.** The chart sets `runAsNonRoot: true`,
  and Kubernetes rejects an image whose user is a name (`CreateContainerConfigError:
  image has non-numeric user`). Both Dockerfiles use numeric UIDs.

## Secrets

`coin-generator-smtp` in the prod namespace holds the SMTP settings for
"request a print" (D19). The prod values read each key with `optional: true`,
so until it exists the backend logs contact mails instead of sending them;
after adding it, restart the API (`kubectl rollout restart deploy/coin-generator-api
-n coin-generator`) or wait for the next deploy. Seal it with the cluster's
controller (plain `kubeseal` works, see the cluster repo):

```bash
kubectl create secret generic coin-generator-smtp -n coin-generator --dry-run=client -o yaml \
  --from-literal=SMTP_HOST=smtp.example.com --from-literal=SMTP_PORT=587 \
  --from-literal=SMTP_USER=... --from-literal=SMTP_PASSWORD=... \
  --from-literal=SMTP_FROM=coins@danielvdspoel.com \
  | kubeseal -o yaml > deploy/cluster/smtp-sealedsecret.yml
kubectl apply -f deploy/cluster/smtp-sealedsecret.yml
```

Previews never send mail: they have no SMTP settings, so the logging mailer
is used.
