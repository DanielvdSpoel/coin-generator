# Cluster CPU right-sizing snapshot (2026-09-28)

Source: Prometheus in `monitoring`. `req` = per-replica CPU request, `peak` = highest 5-minute
average over the last 7 days for that container, `suggest` = `max(10m, ceil(1.5 × peak))` rounded
up to 10m, a request that still leaves headroom. Apply in each app's chart values in
`../upcloud-cluster`. Limits are untouched.

| namespace | workload | container | replicas | req | peak | suggest | frees |
|---|---|---|---|---|---|---|---|
| portfolio | portfolio-app | portfolio | 3 | 100m | 1m | 10m | 270m |
| opruimcoach | opruimcoach-voor-thuis-app | opruimcoach-voor-thuis | 2 | 100m | 2m | 10m | 180m |
| budgetbunny | budgetbunny-ml | web-service | 2 | 100m | 12m | 20m | 160m |
| rybbit | rybbit-backend | backend | 2 | 100m | 12m | 20m | 160m |
| cnpg-system | cnpg-controller-manager | manager | 1 | 100m | 3m | 10m | 90m |
| kube-system | coredns | coredns | 1 | 100m | 4m | 10m | 90m |
| coin-generator-preview | pr-1-api | api | 1 | 100m | 0m | 10m | 90m |
| budgetbunny | dragonfly-budgetbunny-0 | dragonfly | 1 | 100m | 9m | 20m | 80m |
| rybbit | dragonfly-rybbit-0 | dragonfly | 1 | 100m | 9m | 20m | 80m |
| rybbit | dragonfly-rybbit-1 | dragonfly | 1 | 100m | 11m | 20m | 80m |
| budgetbunny | dragonfly-budgetbunny-1 | dragonfly | 1 | 100m | 16m | 30m | 70m |
| loki | loki-0 | loki | 1 | 100m | 20m | 30m | 70m |
| monitoring | prometheus-kube-prometheus-stack-prometheus-0 | prometheus | 1 | 200m | 85m | 130m | 70m |
| postgres | apps-cluster-1 | postgres | 1 | 100m | 17m | 30m | 70m |
| postgres | apps-cluster-2 | postgres | 1 | 100m | 14m | 30m | 70m |
| postgres | apps-cluster-3 | postgres | 1 | 100m | 23m | 40m | 60m |
| rybbit | rybbit-client | client | 2 | 100m | 43m | 70m | 60m |
| mailbunny-preview | pr-97-api-scheduler | scheduler | 1 | 50m | 5m | 10m | 40m |
| whoami | whoami | whoami | 1 | 50m | 1m | 10m | 40m |
| kwekerijvh | kwekerijvh-worker | kwekerijvh-worker | 1 | 50m | 7m | 10m | 40m |
| kube-system | sealed-secrets-controller | controller | 1 | 50m | 1m | 10m | 40m |
| uptime-kuma | uptime-kuma | tailscale | 1 | 50m | 4m | 10m | 40m |
| loki | loki-results-cache-0 | memcached | 1 | 50m | 0m | 10m | 40m |
| loki | loki-chunks-cache-0 | memcached | 1 | 50m | 3m | 10m | 40m |
| budgetbunny | budgetbunny-frontend | web-service | 2 | 25m | 0m | 10m | 30m |
| mailbunny-preview | pr-97-postgres | postgres | 1 | 50m | 9m | 20m | 30m |
| budgetbunny | budgetbunny-backend-scheduler | scheduler | 1 | 50m | 8m | 20m | 30m |
| uptime-kuma | uptime-kuma | uptime-kuma | 1 | 50m | 10m | 20m | 30m |
| budgetbunny | budgetbunny-backend-worker | worker | 1 | 50m | 11m | 20m | 30m |
| mailbunny-preview | pr-97-api-web | web | 1 | 50m | 14m | 30m | 20m |
| clickhouse | chi-rybbit-analytics-0-0-0 | clickhouse-backup | 1 | 50m | 15m | 30m | 20m |
| mailbunny-preview | pr-97-web | web | 1 | 25m | 0m | 10m | 15m |
| mailbunny-preview | pr-97-api-worker | worker | 1 | 25m | 1m | 10m | 15m |
| kwekerijvh | kwekerijvh-scheduler | kwekerijvh-scheduler | 1 | 50m | 23m | 40m | 10m |
| uptime-kuma | autokuma | autokuma | 1 | 20m | 1m | 10m | 10m |
| mailbunny-preview | pr-97 | redis | 1 | 25m | 10m | 20m | 5m |
| kube-system | reflector | reflector | 1 | 25m | 9m | 20m | 5m |
| loki | alloy | config-reloader | 3 | 10m | 0m | 10m | 0m |
| dragonfly-operator-system | dragonfly-operator-controller-manager | manager | 1 | 10m | 1m | 10m | 0m |
| budgetbunny | budgetbunny-backend-web | web | 2 | 100m | 61m | 100m | 0m |
| monitoring | tailscale | tailscale | 1 | 10m | 6m | 10m | 0m |
| monitoring | kube-prometheus-stack-grafana | grafana | 1 | 50m | 28m | 50m | 0m |
| coin-generator-preview | pr-1-web | web | 1 | 10m | 0m | 10m | 0m |
| dragonfly-operator-system | dragonfly-operator-controller-manager | kube-rbac-proxy | 1 | 5m | 0m | 5m | 0m |
| pelican | pelican | pelican | 1 | 100m | 77m | 100m | 0m |
| kwekerijvh | kwekerijvh-backend | kwekerijvh | 2 | 100m | 78m | 100m | 0m |
| clickhouse | chi-rybbit-analytics-0-0-0 | clickhouse | 1 | 150m | 132m | 150m | 0m |

**Total freed if all suggestions are applied: ~2.3 cores** of 6 allocatable.

Notes:
- Values under 10m are meaningless for scheduling; 10m is the floor.
- Databases (postgres, clickhouse, dragonfly) and Prometheus deserve more headroom than 1.5× because their
  peaks are bursty; treat their suggestions as a lower bound.
- Without metrics-server, `kubectl top` does not work; this table is the substitute. Installing
  metrics-server also enables the HPA for coin-generator (phase 8) and VPA in recommendation mode,
  which produces this table continuously.
