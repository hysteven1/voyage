#!/usr/bin/env bash
set -euo pipefail
chart=infrastructure/helm/voyage
rendered=$(mktemp -d)
trap 'rm -rf "$rendered"' EXIT
actionlint .github/workflows/*.yml
docker compose config --quiet
helm lint "$chart" -f "$chart/values-development.yaml"
helm template voyage "$chart" -n voyage-dev -f "$chart/values-development.yaml" > "$rendered/development.yaml"
helm lint "$chart" -f "$chart/values-production.yaml" \
  --set images.api.tag=sha-0000000000000000000000000000000000000000 \
  --set images.worker.tag=sha-0000000000000000000000000000000000000000 \
  --set images.web.tag=sha-0000000000000000000000000000000000000000 \
  --set config.temporalAddress=temporal.example.invalid:7233 --set config.temporalNamespace=example
helm template voyage "$chart" -n voyage-prod -f "$chart/values-production.yaml" \
  --set images.api.tag=sha-0000000000000000000000000000000000000000 \
  --set images.worker.tag=sha-0000000000000000000000000000000000000000 \
  --set images.web.tag=sha-0000000000000000000000000000000000000000 \
  --set config.temporalAddress=temporal.example.invalid:7233 --set config.temporalNamespace=example \
  --set ingress.enabled=true --set networkPolicy.enabled=true > "$rendered/production.yaml"
kubeconform -strict -summary -kubernetes-version 1.34.0 "$rendered" infrastructure/local/dependencies.yaml
# Missing image revisions must be rejected rather than silently using latest.
if helm template invalid "$chart" > /dev/null 2>&1; then
  echo 'ERROR: chart accepted unspecified images' >&2
  exit 1
fi
