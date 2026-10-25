# Voyage web

Next.js App Router, TypeScript, Material UI, local city/airport autocomplete and
legacy/expanded itinerary renderers. Node 24.22.1 and npm; package-lock.json is the
source of dependency versions. System fonts require no external font downloads.

```bash
cd apps/web
npm ci
npm run dev
```

The browser uses same-origin `/api/v1` requests. The Next server forwards them to
`API_INTERNAL_URL` (default http://localhost:8000). Start the API separately for
real planning. `NEXT_PUBLIC_API_URL` is an optional build-time direct-API override;
it is not needed for Compose/Kubernetes. `/api/locations` uses bundled datasets.

```bash
npm run lint
npm run typecheck
npm run test:locations
npm run test:proxy
npm run build
npx playwright install --with-deps chromium
npm run test:ui
```

Type checking generates Next.js route types first, so it works in a fresh checkout.
Browser tests mock the planning API and use a fixed clock. The proxy test creates
a temporary local server. The production Docker image uses Next standalone output
and runs as UID 10001; `npm run dev` remains for native hot reload only.
See [the root README](../../README.md) for deployment and data limitations.
