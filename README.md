# Voyage

AI-powered travel planning platform.

Voyage helps travelers discover flights, accommodations,
transportation, and activities, then generates personalized
itineraries based on budgets, dates, and preferences.

## Tech Stack

- Python / FastAPI
- Next.js / TypeScript
- PostgreSQL
- Temporal
- OpenAI API
- Docker / Kubernetes
- Helm / Argo CD
## Flexible trip planner

The web app has two steps: journey details (including flight preferences) and
travel style. It proposes the route, saves the trip and starts planning automatically. Expanded trips use `options` on the existing trip API. Older requests
with `origin`, `destination`, dates, travelers, budget and preferences remain valid;
existing saved itineraries retain their original renderer and planning behavior.

- `POST /api/v1/trips/route-proposal` accepts the trip fields plus `options.route`
  (a list of locations). It returns suggested order, nights, travel modes, transit
  nights, assumptions and the proposal source. It does not save a trip.
- The web app passes the proposal to `POST /api/v1/trips` to save the route.
  Stays plus transit nights must equal the trip's date window. Expanded trips can omit the budget amount. New UI amounts are soft targets;
  older API requests retain their existing ceiling behavior.
- The existing `POST /api/v1/trips/{id}/plan` generates and atomically persists the
  plan. Version 2 itineraries contain travel legs, stays, grouped daily suggestions,
  rainy-day alternatives, rental searches and group/destination cost estimates.
- Changes after generation create a new trip. Failed planning attempts can be
  retried; `planning_error` on the trip provides a safe explanation when available.

### Data and estimates

Both the API and worker optionally use `OPENAI_API_KEY` and `OPENAI_MODEL` (already
wired through Compose). The API uses structured route suggestions; the worker
suggests varied daily clusters across each city, with visit and transfer durations,
and optional full-day excursions. With no key or an unavailable model, offline route
suggestions and destination templates are used. Tokyo has a reference itinerary
covering different districts, Sunshine City, Hakone and a choice of Disney parks;
other destinations use general outlines. Photo stops such as Hachiko get minutes,
while theme parks and distant excursions occupy their own days. Restaurants and
food interests are excluded; meal allowances remain in the cost estimate. Offline country-to-city and route geography coverage
is deliberately limited; unknown routes retain the entered order and require review.
AI suggestions are not a verified map, timetable, review feed, or availability feed.
Notes are advisory; conflicts surfaced by AI require correction. Traveler review
and booking-site confirmation remain necessary, especially without AI configured.

Costs are illustrative USD estimates, including children. Travelers choose a
per-person or whole-group target, or leave the amount blank. Per-person estimates
split shared costs evenly; individual spending can differ. Spending style defaults
to good value, with budget-conscious and upscale alternatives. Styles adjust room,
food, transport and activity allowances; good-value defaults are $110 per room/night
(up to four guests per room as an allowance), $40 per traveler/day for food,
$65 per car/day, and 15% contingency. Transport uses
rough distance-based estimates when coordinates are known, otherwise fallback
allowances. Optional rainy-day swaps are excluded from the total. New UI targets can be exceeded with a clear notice in the itinerary. Existing
strict/flexible API ceilings remain supported and are never silently exceeded. Selected flight and stay quotes are mixed with estimates for other expenses when
SerpApi is configured. Booking links do not create reservations. Accessibility,
actual room/vehicle capacity, child fares, fees and travel restrictions must be checked
with providers. There is no live weather integration.

### Running the update

Before replacing the worker, ensure no planning workflows are active; this release
changes workflow activity arguments and registration. Deploy the database migration
before starting the updated API/worker, then test with a newly created trip:

```bash
docker compose build api worker web
docker compose run --rm migrate
docker compose up -d api worker web
```

The migration adds nullable `options` and `planning_error` columns and allows omitted
origins. Existing trip rows and itinerary JSON are preserved. Use workflow versioning
before deploying across long-running active executions in production.

The portable planning contract lives in both Python service build contexts as
`app/planning.py` and `app/day_planning.py`; update both copies together. A contract
test checks they match.

### Checks

```bash
cd services/trip-service
.venv/bin/python -m pytest
.venv/bin/ruff check app tests
cd ../planning-worker
.venv/bin/python -m pytest
.venv/bin/ruff check app tests
cd ../../apps/web
npx tsc --noEmit
npm run lint
npm run build
```

The production frontend build needs an environment that permits Turbopack's local
build processes. System fonts are used; no external font downloads are required.
API and persistence unit tests mock database connections; a live PostgreSQL/Temporal smoke test is still
needed before rollout.

## Form and UI redesign

The frontend uses Material UI with a shared warm, responsive theme. Clicking the
travel dates opens a visual calendar: choose departure, then return. Location
fields provide keyboard-accessible city/country suggestions as you type, including
accent-insensitive matching and commonly visited cities ranked first.

Location search runs at `/api/locations` inside Next.js against the bundled
`cities.json` GeoNames dataset; it needs no API key or runtime third-party geocoding
calls. Only ten matching suggestions are returned to the browser, and manual entry
remains available. GeoNames / CC BY 4.0 attribution appears in the footer. The data
covers cities and countries, rather than street addresses or airport codes.

The end-of-journey selector has been removed. Flying and driving trips default to
returning to origin. Already-there trips skip outbound and return travel. The API
continues to support the previous endpoint options for existing callers.

To refresh the UI in Docker after pulling these changes:

```bash
docker compose up -d --build web
```

Frontend checks and interaction tests:

```bash
cd apps/web
npm ci
npm run test:locations
npx playwright install --with-deps chromium
npm run test:ui
npx tsc --noEmit
npm run lint
npm run build
```

The browser tests exercise desktop and mobile forms, real autocomplete searches,
calendar selection, validation, and mocked proposal/save/generate requests. They do not
call live planning services or create trips in PostgreSQL. The frontend now uses
system fonts, so Google Fonts access is not required to build or display the app.


### Latest form simplification

The header is a wordmark and tagline; the sidebar shows the route and dates live,
then company, pace and interests on the second step. It does not show a default
budget. Already-there trips hide the origin input and use “Where”. Filled locations
do not repeat search guidance. Date selection highlights both endpoints and every
day in between, including when the selection is reopened across months.

Flight preferences are collected once on the first step and applied to all flight
searches. The separate “Make it yours” route screen has been removed. Interests
are optional; relaxation is represented by the pace choice rather than an interest.
The internal lodging value `apartment` is retained for API compatibility and shown
as “Vacation rentals”.

Optional budget amounts require the new nullable-budget migration. To update Docker:

```bash
cd ~/projects/voyage
docker compose build api worker web migrate
docker compose run --rm migrate
docker compose up -d api worker web
```

The new API options are `budget_basis` (`per_person`/`group`), `spending_style`
(`budget`/`value`/`upscale`), and `budget_enforcement` (`target`/`ceiling`). Existing
API requests default to group amounts and ceiling enforcement; the new UI sends
per-person targets by default, without requiring an amount. No migration rewrites
existing budgets or itineraries.


### Live flight and stay recommendations

Set `SERPAPI_API_KEY` in the root `.env` for Docker Compose, or in
`services/planning-worker/.env` when running the worker directly. Both files are
ignored by Git. The key is only passed to the worker; it is never sent to the browser.
Recreate the worker after changing its environment:

```bash
docker compose up -d --build worker web
```

The worker searches SerpApi's Google Flights engine for each flight leg, checks local
flight times, dates, connections and overnight preferences, and retrieves a link
pinned to the selected flight numbers. It keeps a separate filtered alternatives
link. Stays use Google Hotels searches with dates, guest counts and a 4+ guest rating
filter, then select a named property with at least 30 reviews. Property details
supply booking links and rates; separate Google Hotels and dated Airbnb links offer
alternatives. Vacation rentals also require a reported capacity sufficient for the
party. This is a Google Hotels/vacation rental integration, not a direct Airbnb feed.
See the [Google Flights API](https://serpapi.com/google-flights-api) and
[Google Hotels API](https://serpapi.com/google-hotels-api) documentation.

Retrieved quotes update the budget, including contingency and per-person amounts.
Multiple-room hotel quotes require manual capacity confirmation; their existing
group allowance is retained rather than treating one room's rate as a group total.
When a search fails, has no matching offer, or the key is absent, the plan retains
estimates and clearly shows that a live recommendation was unavailable. A route
search is never labeled as a selected-flight link. Dates/filters on fallback search
links may need reapplying at the booking site. Prices and availability can change.

Each planning activity has a limit of 40 provider requests and at most four concurrent
searches; a selected option typically needs a search and detail request, plus flight
location lookups. These calls count against the configured SerpApi account's quota.
Only new planning runs receive recommendations; saved itineraries are preserved.
The added selection activity has a Temporal patch marker for existing histories.
Earlier itinerary schema changes still require checking for active workflows before
replacing the worker.

The Tokyo reference uses planning duration estimates, not verified opening times or
reservations. Official references include [Tokyo Disney Resort](https://www.tokyodisneyresort.jp/en/),
[Sunshine Aquarium](https://sunshinecity.jp/en/aquarium/),
[Sunshine 60 Observatory](https://sunshinecity.jp/en/observatory/),
[Shinjuku Gyoen](https://fng.or.jp/shinjuku/en/) and
[Hakone Open-Air Museum](https://www.hakone-oam.or.jp/en/).
