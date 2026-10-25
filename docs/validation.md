# Validation evidence and remaining actions

Local verification performed on 2026-10-25. This records observed results, not a
claim of public production deployment. Existing Compose PostgreSQL/Temporal volumes
were not mounted, removed, reset, migrated or otherwise modified by these tests.

| Check | Observed result |
| --- | --- |
| API locked install (uv --locked, cached offline install) | Passed |
| Worker locked install | Passed |
| Ruff, both Python services | Passed |
| API pytest | 49 passed; one upstream Starlette/httpx deprecation warning |
| Worker pytest | 77 passed |
| ESLint / TypeScript | Passed |
| Location tests | 7 passed |
| API proxy test | Passed against a temporary local HTTP server |
| Playwright desktop/mobile | 32 passed initially and 32 passed again with CI-mode same-origin configuration |
| Native Next production build | Passed after clearing a sandbox-generated failed cache |
| Production container builds | API, worker and web passed with locked installs and pinned bases |
| Web runtime | Homepage, location API and health returned 200 as UID 10001 with read-only root |
| actionlint | All three workflows passed |
| Docker Compose config | Passed; live Compose stack not restarted |
| Tool installer | Download/checksum/install path passed |
| Helm lint/render | Development and production configurations passed |
| Kubernetes schemas | 30 built-in resources valid, 0 invalid/errors/skipped, including GitOps rendering and optional ingress/policy |
| Missing image revisions | Chart rejects unspecified versions |
| kind | Kubernetes 1.34.0 cluster created with pinned node image |
| Local dependencies | PostgreSQL and separate persisted development Temporal healthy |
| Helm first install | Migration hook and application readiness passed |
| Helm upgrades | Revisions 2 and 3 succeeded; Alembic at f8b4a1c209e6 (head) |
| Persistence across upgrade | Previously generated itinerary remained retrievable |
| Full infrastructure smoke | Real web proxy → API → PostgreSQL/Temporal/worker → persisted synthetic itinerary; repeat completed-plan request reused result |
| Argo resources | Server-side dry run passed against pinned official Application/AppProject CRDs |
| Repository | git diff --check passed; documentation links checked |

The kind sequence was run incrementally using the documented commands. The fresh
cluster wrapper was syntax-checked; it was not rerun as a second complete fresh
cluster after the incremental validation. The first local Temporal attempt exposed
Go's need for USER when running a numeric non-root UID; the committed manifest fixes
it. That Pod was recreated with the same PVC, preserving data. Worker startup
retries recovered once Temporal was available. No paid provider calls were made.

The local cluster `voyage-infra` is left running for inspection. Its kubeconfig is
`/tmp/voyage-infra.kubeconfig`; it is not in Git. Dependencies and PVCs remain.
Use [the explicit cleanup procedure](kubernetes.md#safe-cleanup) only when you
intend to discard that disposable cluster's data.

## Not verified here

- GitHub-hosted Actions execution, GHCR publication, repository protection settings,
  Dependabot execution, registry authentication or image pulls from private GHCR.
- Running Argo controller/repo-server, actual GitHub source retrieval, reconciliation,
  synchronization, or GitOps rollback. Only manifests/CRDs/rendering were validated.
- Paid expanded AI planning, live SerpApi availability or model-account permissions.
- A cloud deployment, production Temporal, external PostgreSQL/TLS, ingress controller,
  DNS, certificates, access gateway, network-policy enforcement, HA or load capacity.
- Backup restore drills, production rollback/replay compatibility and alert delivery.

## Manual completion checklist

- [ ] Review the focused local commits and [security limits](operations.md).
- [ ] Push a review branch and merge through a PR. For example:
  `git push origin HEAD:infra/voyage-devops`, then open a PR targeting main.
- [ ] Confirm CI passes on GitHub; run the manual Integration smoke workflow.
- [ ] Enable the documented main/release-tag rules and required `CI passed` check.
  No repository settings were changed by the implementation.
- [ ] Confirm successful-main publishing creates the three GHCR packages; configure
  their visibility/access inheritance or create an external imagePullSecret.
- [ ] If desired, create a protected `vX.Y.Z` tag on a validated main commit to verify
  release publication. Do not create tags simply to bypass a failed CI run.
- [ ] Follow [Argo bootstrap](gitops.md) after the chart exists on remote main. Build
  and load the pinned local revision, or promote the actually published GHCR SHA/
  digests in a reviewed values change. Review diff and manually Sync.
- [ ] Add provider keys securely only if you want a paid end-to-end UI demonstration.
- [ ] Before public hosting, add access protection, provider usage limits, TLS,
  durable external dependencies and tested backups. Approve any cloud resources
  separately; this implementation did not provision them.

These are external execution/approval steps, not missing local infrastructure files.
