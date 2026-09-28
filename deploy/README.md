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

## Day to day

- Previews: automatic. The sticky PR comment carries the URL and image tags.
- Prod: merge to `main`. The workflow waits for the rollout and smoke-tests
  `/api/health`; on failure it runs `helm rollback`.
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

## Secrets

None in phase 0. The contact email (phase 7/8) adds a `coin-generator-smtp`
SealedSecret in the prod namespace; previews use the logging mailer.
