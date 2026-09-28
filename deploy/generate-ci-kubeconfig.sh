#!/usr/bin/env bash
#
# Generate the kubeconfig that GitHub Actions uses to deploy Coin Designer environments (run once per namespace).
#
# Creates a namespace-scoped ServiceAccount ("github-deployer") with admin
# rights *inside the target namespace only*, plus a long-lived token, and
# writes a kubeconfig built from that token.
#
# Idempotent: it reuses the same ServiceAccount and token Secret on every run,
# so re-running produces the SAME kubeconfig instead of minting a new identity.
# Run it once to bootstrap; re-run any time to regenerate the file (e.g. after
# rotating the token or losing the local copy).
#
# Usage:
#   NS=coin-generator-preview deploy/generate-ci-kubeconfig.sh --set-secret KUBECONFIG_PREVIEW
#   NS=coin-generator         deploy/generate-ci-kubeconfig.sh --set-secret KUBECONFIG_PROD
#
#   Without --set-secret it writes ci-kubeconfig.yaml (gitignored) for you to upload
#   by hand: gh secret set KUBECONFIG_PREVIEW < ci-kubeconfig.yaml && rm ci-kubeconfig.yaml
#
# Requires: kubectl (pointed at the target cluster), and gh for --set-secret.

set -euo pipefail

NS="${NS:-coin-generator-preview}"
SA="${SA:-github-deployer}"
OUT="${OUT:-ci-kubeconfig.yaml}"
SET_SECRET=0
SECRET_NAME="KUBECONFIG"
if [[ "${1:-}" == "--set-secret" ]]; then
  SET_SECRET=1
  SECRET_NAME="${2:-KUBECONFIG}"
fi

echo "==> Ensuring ServiceAccount ${NS}/${SA} and namespace-admin binding"
# `apply` (not `create`) so re-running never errors on already-existing objects.
kubectl apply -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ${SA}
  namespace: ${NS}
---
# Namespace-admin only: full rights inside ${NS}, nothing cluster-wide. helm
# needs to CRUD deployments/services/ingress/configmaps/secrets (release state
# is stored as Secrets here) and read pods for --wait.
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: ${SA}-admin
  namespace: ${NS}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: admin
subjects:
  - kind: ServiceAccount
    name: ${SA}
    namespace: ${NS}
---
# K8s 1.24+ doesn't auto-mint SA token Secrets. This bound Secret holds a
# long-lived token that does NOT expire (unlike \`kubectl create token\`), which
# is what a long-running CI needs. Reusing this Secret keeps the token stable
# across re-runs of this script.
apiVersion: v1
kind: Secret
metadata:
  name: ${SA}-token
  namespace: ${NS}
  annotations:
    kubernetes.io/service-account.name: ${SA}
type: kubernetes.io/service-account-token
EOF

echo "==> Waiting for the token controller to populate the Secret"
for i in {1..30}; do
  TOKEN_B64="$(kubectl -n "$NS" get secret "${SA}-token" -o jsonpath='{.data.token}' 2>/dev/null || true)"
  [[ -n "$TOKEN_B64" ]] && break
  sleep 1
done
if [[ -z "${TOKEN_B64:-}" ]]; then
  echo "ERROR: token Secret ${NS}/${SA}-token was never populated." >&2
  exit 1
fi

SERVER="$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')"
CA="$(kubectl -n "$NS" get secret "${SA}-token" -o jsonpath='{.data.ca\.crt}')"   # already base64
TOKEN="$(printf '%s' "$TOKEN_B64" | base64 -d)"

echo "==> Writing ${OUT}"
cat > "$OUT" <<EOF
apiVersion: v1
kind: Config
clusters:
  - name: ${NS}
    cluster:
      server: ${SERVER}
      certificate-authority-data: ${CA}
contexts:
  - name: ${NS}
    context:
      cluster: ${NS}
      namespace: ${NS}
      user: ${SA}
current-context: ${NS}
users:
  - name: ${SA}
    user:
      token: ${TOKEN}
EOF

echo "==> Verifying the kubeconfig can reach the namespace"
if KUBECONFIG="$OUT" kubectl -n "$NS" get deploy >/dev/null 2>&1; then
  echo "    OK — token can list deployments in ${NS}"
else
  echo "    WARNING: could not list deployments (network reachability or RBAC?)." >&2
fi

if [[ "$SET_SECRET" == "1" ]]; then
  echo "==> Uploading to the repo's ${SECRET_NAME} secret via gh"
  gh secret set "$SECRET_NAME" < "$OUT"
  rm -f "$OUT"
  echo "    Done. Local ${OUT} removed."
else
  echo
  echo "Next: load it as the repo secret (raw YAML, not base64), then delete the file:"
  echo "    gh secret set ${SECRET_NAME} < ${OUT} && rm ${OUT}"
fi
