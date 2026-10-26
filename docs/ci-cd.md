# CI and image delivery

`CI` runs on pull requests and pushes to main. It is also reusable by release
publishing. All jobs have `contents: read`, timeouts, and pinned action commits.
No job reads repository provider secrets. Python installs use uv 0.13.5,
Python 3.12, `uv sync --locked --dev --no-install-project`; frontend uses Node
24.22.1 and `npm ci`. Dependency caches are keyed by lockfiles.

Jobs: `Python (trip-service)`, `Python (planning-worker)`, `Web`,
`Container (api)`, `Container (worker)`, `Container (web)`, `Infrastructure`,
and aggregate `CI passed`. The aggregate fails if any prerequisite fails or skips.
No path filters can accidentally bypass required checks. Browser tests use a fixed
clock and mocked planning APIs; unit tests mock external services. These checks do
not prove a live deployment works. Container builds never publish on pull requests.

## Recommended GitHub rules (manual configuration)

In Settings → Rules → Rulesets, target `main`:

- Require a pull request and resolution of review conversations.
- Require `CI passed` from the CI workflow and an up-to-date branch.
- Require one approval if collaborators can review; for a solo repository, keep
  the PR and checks requirement without making self-approval impossible.
- Block deletion and force pushes; apply to administrators when practical.
- Restrict bypass to deliberate emergency recovery, with an audit trail.
- Protect release tags `v*` against unexpected creation, rewriting and deletion.
- Set Actions workflow token defaults to read-only. Publishing grants packages
  write only to its publishing job. Do not enable secrets for fork pull requests.

Dependabot tracks GitHub Actions, npm, uv and Docker weekly. Review lockfile and
major-version changes. Do not enable automatic merges merely to reduce PR counts.
No repository settings have been changed by this implementation.

## Publishing

`Publish images` runs after a successful main-branch CI run, or on `vX.Y.Z` tag
pushes. Tag pushes run the reusable CI workflow first; the publishing job also
verifies the tagged commit belongs to main. Pull requests cannot publish. Tags
outside the stable semantic-version format are rejected. All actions are pinned
to resolved full commit SHAs (reviewed versions are noted in comments).

Images: `ghcr.io/hysteven1/voyage-api`, `voyage-worker`, `voyage-web`.
Each receives `sha-<full 40-character commit>`; a release also receives `X.Y.Z`.
No `latest` tag is published. SHA tags identify source, but registries can overwrite
tags: use the resulting digest in production values for strict content immutability.
The pipeline attaches OCI source/revision metadata, provenance and SBOM attestations.
BuildKit caches are scoped per service. Current builds target linux/amd64 (including
Docker Desktop on x86 WSL2); other cluster architectures require an explicit build.

Only the publishing job has `packages: write`. It authenticates with the ephemeral
`GITHUB_TOKEN`. No PAT, provider credential or Kubernetes credential is needed.
CI never changes the Helm values or deploys a cluster. Promotion is a reviewed Git
change to image tags/digests; production synchronization is manual.

Manual prerequisites: enable Actions, permit this repository's token to publish
packages, and check package access inheritance after first publication. For private
images, provision a namespace-scoped imagePullSecret from an external credential
store; never commit it. The initial local checks did not publish images. A subsequent GitHub main run
successfully published all three images; see [verification evidence](validation.md).

The Infrastructure job runs the checksum-verified tool installer, actionlint,
Compose validation, both Helm environments and Kubernetes schema validation,
including the exact GitOps environment values. `Integration smoke` is manually
triggered to keep routine PR checks lightweight. It creates a fresh local kind
cluster on the runner, tests the synthetic-provider flow through actual services,
and server-validates Argo resources. Only that disposable CI cluster is deleted;
the local script leaves its cluster for inspection. GitHub-hosted CI and publishing have subsequently succeeded. The manual integration
workflow has not yet been run on GitHub; see [verification evidence](validation.md).
