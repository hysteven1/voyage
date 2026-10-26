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

## Follow-up GitHub and GitOps verification

Verified later on 2026-10-25:

- [Main CI passed](https://github.com/hysteven1/voyage/actions/runs/40244895336)
  for `8af67c38821cf55caec36d4c3bccaaf5a5ddf56b`.
- [Image publication succeeded](https://github.com/hysteven1/voyage/actions/runs/40245151389)
  for all three services at that source revision.
- The pinned Argo CD controller was installed into the existing local kind cluster.
  It fetched public GitHub main at that revision and completed a manual sync.
  The Application reported Synced/Healthy; the PreSync migration completed and all
  application/dependency Pods were ready. Auto-sync and pruning remain disabled.
- The deployed image revision is `359cb903d3261160e976b5cc34f9e01cb3f61e1a`,
  matching the development values. Those exact images were built and loaded locally.
- The synthetic-provider smoke test passed after Argo took ownership, and an
  itinerary saved before the handoff remained retrievable. Neither PostgreSQL nor
  Temporal resources/PVCs were deleted or brought under Argo ownership. There were
  no active planning jobs at handoff. The old Helm release record remains; use
  Argo/Git for future changes to those application resources.
- Anonymous GHCR pull inspection returned 401. Publication is verified; registry
  pull access for deployment still needs package visibility or a pull credential.
- GitHub reports no manual Integration smoke runs yet. Its individual local
  infrastructure and Argo steps have been exercised, but hosted dispatch remains.

## Still not verified

- Manual Integration smoke execution on GitHub, repository protection settings,
  registry authentication or image pulls from private GHCR.
- Automatic image promotion, automatic deployments or GitOps rollback.
- Paid expanded AI planning, live SerpApi availability or model-account permissions.
- A cloud deployment, production Temporal, external PostgreSQL/TLS, ingress controller,
  DNS, certificates, access gateway, network-policy enforcement, HA or load capacity.
- Backup restore drills, production rollback/replay compatibility and alert delivery.

## Manual completion checklist

- [ ] Review the focused local commits and [security limits](operations.md).
- [x] Push the infrastructure changes and merge through a PR. For example:
  `git push origin HEAD:infra/voyage-devops`, then open a PR targeting main.
- [ ] Confirm CI passes on GitHub; run the manual Integration smoke workflow.
- [ ] Enable the documented main/release-tag rules and required `CI passed` check.
  No repository settings were changed by the implementation.
- [x] Confirm successful-main publishing completes for all three GHCR images.
- [ ] Configure package visibility/access or create an external imagePullSecret.
- [ ] If desired, create a protected `vX.Y.Z` tag on a validated main commit to verify
  release publication. Do not create tags simply to bypass a failed CI run.
- [x] Bootstrap local Argo, load the pinned local images and manually sync from GitHub.
- [ ] Promote published GHCR images into the approved deployment environment.
- [ ] Add provider keys securely only if you want a paid end-to-end UI demonstration.
- [ ] Before public hosting, add access protection, provider usage limits, TLS,
  durable external dependencies and tested backups. Approve any cloud resources
  separately; this implementation did not provision them.

These are external execution/approval steps, not missing local infrastructure files.

[Step 13](deployment-plan.md) records the remaining live deployment decisions and
acceptance checks. No cloud resources, DNS changes or public runtime services were
created during infrastructure verification.

## Follow-up credential-default remediation

GitGuardian reported a Generic Password in historical Compose commit `1e0eba8`.
The reported value was the hardcoded PostgreSQL development fallback. The local
`.env` configuration matched that default, so it should be treated as disclosed,
even though the database host port is bound to loopback. The reported OpenAI
configuration was an environment-variable reference, not a literal API key.

Current Compose now requires an explicit, nonempty POSTGRES_PASSWORD. Configuration
checks passed for missing/empty rejection and generated-password acceptance; the
infrastructure checks still validated 30 Kubernetes resources. An exact-value scan
found no configured local secret values in the current tracked files. Existing
PostgreSQL roles, .env files, volumes, and Git history were not changed. Removing
the source fallback does not rotate credentials or erase the historical alert.
See [operations](operations.md) before rotating an initialized database.
