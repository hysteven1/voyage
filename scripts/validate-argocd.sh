#!/usr/bin/env bash
# Server validation in the dedicated local cluster; installs CRDs only, no controller.
set -euo pipefail
revision=c2b1e3017e2cec86b122172e861dcd026453ae44 # Argo CD v3.5.6
kubectl --context kind-voyage-infra apply --server-side -f "https://raw.githubusercontent.com/argoproj/argo-cd/$revision/manifests/crds/application-crd.yaml"
kubectl --context kind-voyage-infra apply --server-side -f "https://raw.githubusercontent.com/argoproj/argo-cd/$revision/manifests/crds/appproject-crd.yaml"
kubectl --context kind-voyage-infra wait --for=condition=Established crd/applications.argoproj.io crd/appprojects.argoproj.io --timeout=60s
kubectl --context kind-voyage-infra create namespace argocd --dry-run=client -o yaml | kubectl --context kind-voyage-infra apply -f -
kubectl --context kind-voyage-infra apply --dry-run=server -f infrastructure/argocd/
