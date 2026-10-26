# Step 13: live deployment plan

Voyage targets a few private users. The deployment should be affordable and easy
to recover, while retaining the CI/Kubernetes/GitOps work as demonstrable engineering.
This is a plan, not authorization to buy hosting, change DNS, expose a service, or
make paid provider calls.

## Infrastructure verification before hosting

Verified on 2026-10-25:

- Main CI succeeded for `8af67c38821cf55caec36d4c3bccaaf5a5ddf56b`:
  [CI run](https://github.com/hysteven1/voyage/actions/runs/40244895336).
- All three image-publishing jobs completed successfully:
  [Publish images run](https://github.com/hysteven1/voyage/actions/runs/40245151389).
- Local Argo CD fetched that Git revision and manually synchronized Voyage.
  The Application reached Synced/Healthy, including the migration hook.
  Development uses locally loaded images from the revision pinned in its values.
- Application PostgreSQL and Temporal storage remained independent of Argo;
  existing itinerary data survived the handoff. The no-key synthetic smoke test
  exercises the real infrastructure rather than mocked DB/workflow calls.

Remaining external checks: run the manual Integration smoke workflow on GitHub,
verify package access, and configure branch protection if not already done.
Anonymous GHCR pulls returned 401 during inspection. Successful publication does
not establish that a new server can pull the images. Choose public packages or
provision a protected registry pull credential; changing repository visibility
alone does not establish package visibility.

## 1. Choose the hosting model and budget

Agree on a monthly budget, region, whether a domain is already owned, and whether
the live deployment should demonstrate Kubernetes/Argo or prioritize the smallest
operational footprint. Compare a single server running Compose with a small
Kubernetes installation; a managed multi-node cluster is not required for the
expected workload. Confirm current pricing, storage, backups and network charges
before purchase. No provider is selected or provisioned by this document.

## 2. Provision and secure the environment

Create the approved server/cluster, configure SSH/admin access and updates, set
firewall rules, and allocate persistent storage. Expose only the intended web
entrypoint and required admin access. Keep PostgreSQL, Temporal, Argo and internal
API services private. Do not expose the Kubernetes API or dashboards broadly.

Set resource limits and confirm storage capacity. Decide how hosts restart and
recover after a reboot. Use fresh deployment credentials; never reuse the committed
local development database password on an externally accessible service.

## 3. Deploy stateful dependencies and migrate safely

Choose application PostgreSQL and a production-capable Temporal service separately.
The local SQLite development server is not the production configuration. If
self-hosting, Temporal needs its own supported persistence and schema lifecycle.
Confirm the costs and complexity before choosing self-hosted versus managed.

Provision Secrets outside Git, including database URL, provider keys, Temporal
credentials and any registry pull credential. Configure namespaces and TLS as
appropriate. Decide whether existing local trip data should be migrated; do not
copy or reset it implicitly. Run the serialized Alembic upgrade Job before the
application rollout. Never reverse migrations automatically during image rollback.

## 4. Connect delivery and define promotion

First verify that the target can pull all three exact published image revisions.
Commit the chosen endpoints and image digests in a reviewed environment values
file, without credentials. Create the explicitly approved Argo destination and
project permissions for that environment. The existing project permits local
voyage-dev only; it is intentionally not a production deployment declaration.

Current delivery is:

`merge → CI → GHCR image publication → reviewed Git values change → manual Argo sync`

If automatic deployment is desired, specify what promotes the new image into Git.
Argo auto-sync alone does not change the pinned image revision when CI publishes.
A straightforward approach is a promotion PR updating all three image digests;
merging the approved PR authorizes deployment, and Argo reconciles that declared
state. Keep production promotion protected and avoid an uncontrolled deploy of
every published image. This additional promotion automation is not implemented yet.

## 5. Configure domain, HTTPS and private access

Configure DNS, ingress/reverse proxy, certificate issuance and renewal. Put the
web app behind an authenticated access gate with an allowlist for the intended
friends. This avoids needing a full account system immediately, but authorized
users still share access to trips because the app has no per-trip ownership model.
Protect all application routes, including the paid route/planning endpoints.

## 6. Add lightweight operating safeguards

- Bound paid requests and concurrent planning jobs; do not treat a credit balance
  as the only cost control. Account-level usage alerts complement application limits.
- Back up the application database and Temporal persistence independently. Store
  backups outside the main server and perform a restore into a separate environment.
- Monitor web health, failed plans, worker availability, disk space and certificate
  renewal. Keep logs useful without printing credentials or traveler notes.
- Document image rollback, schema compatibility, workflow replay constraints,
  credential rotation, and what to do when the host or provider fails.

These can be small, practical controls. A service mesh, HA cluster, full account
system and large metrics stack are not prerequisites for a friends-only demo.

## 7. Run the live acceptance test

Verify HTTPS, access denial for unauthorized users, page/autocomplete behavior,
API/worker readiness, migration completion and data persistence. Run the synthetic
smoke test first. Then, with explicit approval for provider usage, create a short
real trip through the web form and inspect route generation, flights/stays,
budget estimates and daily recommendations. Check failure/retry behavior and
confirm a server/Pod restart preserves saved itineraries.

Finally, promote a new image through the actual pipeline, observe rollout health,
and test an application rollback without changing the DB schema or erasing
Temporal history. Record what was tested and the commit/digests deployed.

## Completion criteria

Step 13 is complete when the approved live URL is private to the intended users,
HTTPS renews correctly, the target pulls pinned images, trips complete and persist,
backups can be restored, promotion/rollback has been demonstrated, and ongoing
hosting/provider costs are understood. A successful homepage response alone is not
an end-to-end deployment test.
