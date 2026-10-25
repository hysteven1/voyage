# Argo CD GitOps

Git declares the chart, values, image revisions and Application. Publishing images
does not change deployment values. `infrastructure/argocd/project.yaml` allows only
this repository, the local voyage-dev namespace, and the resource kinds the chart
needs. It cannot deploy to production or manage cluster-wide resources/Secrets.
The Application uses manual synchronization and no cascading-delete finalizer.

The Application is named `voyage`, matching Helm's releaseName so Argo label
tracking cannot change chart selectors. Environment values live separately under
`infrastructure/environments/`. Development pins source revision
`359cb903d3261160e976b5cc34f9e01cb3f61e1a`, the verified infrastructure implementation,
with locally loaded images. It does not assume GHCR has published historical commits.

## Bootstrap a local demonstration

First complete [local Kubernetes setup](kubernetes.md). The repo changes must be
reviewed and pushed/merged to GitHub before Argo can fetch them; an unpushed local
working tree is not GitOps source. If the repository is private, configure read-only
repository access through Argo's UI/credential store, not a committed Secret.

Build exactly the source selected in the development values. `git archive` excludes
untracked files and `.env` files; this separate temporary directory does not change
your checkout:

```bash
export KUBECONFIG=/tmp/voyage-infra.kubeconfig
export PATH=/tmp/voyage-tools:$PATH
revision=359cb903d3261160e976b5cc34f9e01cb3f61e1a
build_dir=$(mktemp -d /tmp/voyage-gitops-build.XXXXXX)
git archive "$revision" | tar -x -C "$build_dir"
docker build -t "voyage-api:sha-$revision" "$build_dir/services/trip-service"
docker build -t "voyage-worker:sha-$revision" "$build_dir/services/planning-worker"
docker build -t "voyage-web:sha-$revision" "$build_dir/apps/web"
kind load docker-image --name voyage-infra \
  "voyage-api:sha-$revision" "voyage-worker:sha-$revision" "voyage-web:sha-$revision"

kubectl --context kind-voyage-infra create namespace argocd --dry-run=client -o yaml | kubectl --context kind-voyage-infra apply -f -
kubectl --context kind-voyage-infra -n argocd apply --server-side \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/c2b1e3017e2cec86b122172e861dcd026453ae44/manifests/install.yaml
kubectl --context kind-voyage-infra -n argocd rollout status deployment/argocd-server --timeout=5m
kubectl --context kind-voyage-infra -n argocd apply -f infrastructure/argocd/project.yaml
kubectl --context kind-voyage-infra -n argocd apply -f infrastructure/argocd/development.yaml
kubectl --context kind-voyage-infra -n argocd port-forward svc/argocd-server 8080:443
```

The installation is pinned to Argo CD v3.5.6's full source commit. Review upstream
security updates before installing later. Open https://localhost:8080 and accept
the local development certificate. Retrieve the initial admin password locally
using the official Argo CD initial-login procedure, change it, and do not include
it in repository files, screenshots or logs. No ingress for Argo is configured.

If you installed Voyage with Helm first, wait for active workflows to finish, then
uninstall only the application (`helm uninstall voyage --kube-context
kind-voyage-infra -n voyage-dev`) before the first Argo sync. The separately managed
PostgreSQL/Temporal StatefulSets and their data remain. Do not uninstall dependencies
or delete PVCs. Once Argo owns the application, manage it through Git/Argo only.

In Argo, review the diff and select **Sync** for `voyage`, initially without prune.
The Helm pre-install/pre-upgrade migration Job maps to Argo PreSync; it uses only
the precreated Secret and existing DB, so first sync works without chart resources.
Wait for Synced/Healthy, then run `python3 scripts/smoke-trip.py` through the web
port-forward. This actual synchronization is a manual remaining step: local
validation does not push your changes or prove remote repository/image access.

## Promotion and rollback

For registry-based development, edit `infrastructure/environments/development.yaml`:
set repositories to `ghcr.io/hysteven1/voyage-{api,worker,web}`, set all tags to the
same published `sha-<full commit>`, and set `imagePullPolicy: IfNotPresent` (or use
image digests). For private GHCR packages set namespace imagePullSecrets too.
Commit the change in a PR, wait for CI, merge, review the Argo diff, then sync.
No image updater rewrites Git automatically.

Local development auto-sync is optional after a successful manual sync. Add an
`automated` policy in a reviewed change if desired. Leave pruning disabled until
you understand its effect. No production Argo Application is included: production
requires explicit destination approval, separate constrained project, external
DB/Temporal, digest-pinned images, TLS and protected promotion reviews.

To roll back, revert the environment image commit in Git and sync. Check schema
and workflow-history compatibility first. Never downgrade a DB or delete Temporal
history to force an old worker to run. With auto-sync enabled, a UI rollback can
be overwritten by Git; revert Git instead. Disable auto-sync before emergency
manual intervention, then reconcile the recovery state back into Git.

## Validation boundaries

`scripts/validate-infrastructure.sh` renders the exact GitOps values and validates
the resulting built-in Kubernetes resources. `scripts/validate-argocd.sh` installs
only the two pinned upstream CRDs into the dedicated kind cluster and performs
server-side dry-run validation of the Application/Project. It does not install an
Argo controller, authenticate to GitHub, pull GHCR images, or synchronize a release.
The manual Integration smoke workflow includes this validation.
