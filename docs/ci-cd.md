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
