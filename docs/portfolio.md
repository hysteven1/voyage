# Portfolio demonstration

A useful five-minute walkthrough:

1. Explain the boundary: Next.js proxies same-origin requests to FastAPI;
   PostgreSQL owns trip data; Temporal owns execution history; workers perform
   planning and external searches. Describe why workflow persistence is separate.
2. Show a pull request's CI jobs and required `CI passed` status after a real
   GitHub run. Explain locked installs, pinned actions, read-only tokens and why
   untrusted pull requests cannot publish. Until pushed, show the local results
   and call the remote pipeline configured but unverified.
3. Show the three image builds, non-root production entrypoints and a digest-pinned
   promotion. Explain that a full source-SHA tag is useful traceability, while a
   registry digest pins content.
4. Show `helm template`, local healthy Pods and the migration Job behavior. Run
   `scripts/smoke-trip.py`, inspect the saved itinerary, and find its
   `plan-trip-<id>` history in Temporal. Identify the smoke test as synthetic.
5. Show the constrained Argo Application and a Git values diff. After a real sync,
   demonstrate Synced/Healthy and rollback by reverting an image promotion in Git.
   Explain that migrations are not automatically reversed.

Discuss tradeoffs candidly: fixed replicas for a small private workload; optional
network policy; no monitoring stack for appearances; local SQLite Temporal only
for learning; external production services; and missing application authorization
and spending controls. Back claims with [verification evidence](validation.md).

Resume wording after local verification:

> Built reproducible CI and GHCR publishing workflows for a Next.js/FastAPI travel
> planner; implemented and locally verified Helm deployment with serialized database
> migrations, durable Temporal orchestration, non-root containers, health probes,
> and a real PostgreSQL/Temporal integration smoke test; configured Argo CD GitOps
> promotion with constrained deployment permissions.

Only describe remote CI publication or Argo synchronization as demonstrated after
performing and recording those steps. Do not claim uptime, user scale, cloud
operation, or production recovery results this project has not measured.
