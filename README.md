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

Both the API and worker optionally use `OPENAI_API_KEY`. `OPENAI_PLANNING_MODEL`
defaults to `gpt-6.1-sol` for route and itinerary reasoning; `OPENAI_MODEL` remains
`gpt-4o-mini` by default for short narrative copy. Both are wired through Compose. The API uses structured route suggestions; the worker
suggests varied daily clusters across each city, with visit and transfer durations,
and optional full-day excursions. Each destination is generated independently, with
its own dates and batches of at most three days. Itinerary generation requires an API
key; provider failures trigger a recovery-model attempt and Temporal retries rather
than successfully persisting missing activity days. Repetitive generic activities are never substituted
for actual recommendations. Photo stops such as Hachiko get minutes,
while theme parks and distant excursions occupy their own days. Restaurants and
food interests are excluded; meal allowances remain in the cost estimate. Offline country-to-city and route geography coverage
is deliberately limited; unknown routes retain the entered order and require review.
AI suggestions are not a verified map, timetable, review feed, or availability feed.
Interests are optional guidance and can be omitted when they do not fit. The route
request excludes activity interests. A blocking AI conflict must concern dates,
transport, required stops or budget and quote an explicit requirement present in
the notes; free-form preference mismatches cannot block planning. Quoted notes
ground the source of a conflict, not factual proof of the model's interpretation.
Date, traveler, route and budget rules are still validated in code. Traveler review
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

Flight preferences are collected once on the first step. The departure-after
window applies only when leaving home; the get-home-by window applies only to the
return flight, in the home airport's local time. Overnight flights
are allowed, without a separate toggle. The separate “Make it yours” route screen has been removed. Interests
are optional; relaxation is represented by the pace choice rather than an interest.
The lodging dropdown and car-rental controls are removed. New plans recommend
hotels and always offer an entire-home Airbnb search for the full group. Legacy
lodging/car options remain readable through the API. Child ages are optional,
with explanatory copy about possible age-dependent fares. If all ages are not
provided, flight quotes use a labeled adult-fare estimate for the whole group.

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

The worker resolves city labels to Google Flights airport groups, rather than requiring
a specific airport. It retries shorter city/country labels when full administrative
labels are not recognized. Each flight leg uses deep search, local times, connections
and overnight preferences, and retrieves a link
pinned to the selected flight numbers. It keeps a separate filtered alternatives
link. Flights are resolved before hotels: actual arrival dates update transit days,
the easy arrival day, stay nights and check-in dates while keeping the trip window fixed.
A failed search is displayed separately from a search returning no matching offers.
Bare Google Flights landing URLs are discarded; fallback searches use Google Search
because the Flights landing page ignores free-text query parameters.
Stays use Google Hotels searches with dates, one representative room for up to
four guests and a 4+ guest rating filter, then select a named property with at
least 30 reviews. A room quote is multiplied by the requested room count for the
group estimate; availability of that many rooms is not assumed to be verified.
Group and per-person estimates are displayed. Property details
supply booking links and rates; separate Google Hotels and dated Airbnb links offer
alternatives. Airbnb links are generated before provider requests and remain
available even when no live hotel quote is retrieved. This is not a direct Airbnb feed.
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

Tokyo reference data is used explicitly by regression fixtures, not automatically
as a replacement for failed AI suggestions. Its estimates are not opening times or
reservations. Official references include [Tokyo Disney Resort](https://www.tokyodisneyresort.jp/en/),
[Sunshine Aquarium](https://sunshinecity.jp/en/aquarium/),
[Sunshine 60 Observatory](https://sunshinecity.jp/en/observatory/),
[Shinjuku Gyoen](https://fng.or.jp/shinjuku/en/) and
[Hakone Open-Air Museum](https://www.hakone-oam.or.jp/en/).


### Itinerary coverage and interests

The AI planner builds a must-see shortlist and day routes for every destination,
using the travel month, stay length, pace and interests. Highlights include reasons
to visit, and scheduled sights can carry a Must-see tag. It requests an explicit
number of daily plans and makes one bounded repair request when days are missing
or packed days are too sparse. If removing an extra excursion leaves a gap, a short
supplemental request asks only for the missing city days, excluding existing attractions. These checks apply to all cities. Missing recommendations remain empty and
are marked incomplete; reference examples are only used explicitly by tests.

Packed pace uses all fitting nearby suggestions, up to 11 hours including travel,
with an AI target of 9–10 hours. Actual visit lengths are preserved, including brief
photo stops. Full-day parks and excursions need no extra city stops. Meal breaks
remain flexible. Suggestions are editorial estimates, not live opening hours or
verified seasonal event listings.

Short stays prioritize city highlights. Day trips are allowed only with at least
four full sightseeing days at that destination, with at most one scheduled excursion
per four full days (maximum two). Arrival and transit days are excluded. Day-trip
alternatives are omitted for short stays, including after flight arrival dates reduce
the available time. A long trip split among short city stays does not automatically
qualify for excursions.

Optional interests now cover Iconic sights, Culture & history, Nature & scenery,
Adventure & hiking, Shopping, Theme parks and Day trips. Blank interests produce a
mix of city highlights. Old `#how-it-works` and `#planner` URLs are normalized to `/`
without changing the query parameters or adding an extra browser history entry.


### Current-session itinerary UI

Selected flights show the airline, flight number, local departure/arrival times,
quote and stops. Duplicate route-duration estimates and search instructions remain
only for unselected options. Airport timezones come from the `airportsdata` IATA
catalog and Python `zoneinfo`/`tzdata`, using the actual travel date for daylight
saving rules; unknown airports are labeled local time rather than guessing a zone.
Selected stays show the property, reviews, quote and one confirmation note, with
estimated allowances retained only when no property recommendation is available.

The itinerary header offers **Edit trip details** (reuse current form values) and
**Plan another trip** (clear the form). No account, saved-trip browser, recovery link,
or browser storage is added. Refreshing starts a blank page. Trips and itinerary
JSON remain in PostgreSQL for future account/history features; the active page
uses its in-memory trip ID to display the generated itinerary.

The stronger planning model was checked against the configured API account and a
short Tokyo trip with Adventure & hiking. This is a paid OpenAI API call, separate
from a ChatGPT/Codex subscription. See the official
[GPT-6.1 Sol model documentation](https://developers.openai.com/api/docs/models/gpt-6.1-sol).
Use `OPENAI_PLANNING_MODEL` to choose another compatible model. Reasoning options
are sent to GPT-5/GPT-6 models; a `gpt-4o-mini` override omits them. Itinerary requests
use low reasoning to reduce response latency, as does the shorter route proposal.


### Multi-city failure handling

A three-city trip previously used one large AI response: a timeout discarded every
city and triggered repetitive generic templates. Cities now run separately with up
to four concurrent requests, each requesting at most three days at a time. Previous
attractions are supplied to subsequent batches to prevent repeats. The primary model
uses low reasoning with a 90-second request timeout. Provider or structured-output
failures get a 60-second recovery attempt using `OPENAI_RECOVERY_MODEL` (default
`gpt-4o-mini`). Failed optional quality repairs preserve the original recommendations.
Unresolved missing days raise an activity error so Temporal retries planning; completion
also rejects incomplete plans before any database write. This cannot guarantee an
external provider is always available, but failures are no longer saved as completed
empty itineraries. Existing completed itineraries are preserved. Route titles are joined from
structured locations with ` → ` instead of trusting AI-generated separators.

Completed city batches are checkpointed with Temporal heartbeats, so an activity
retry resumes instead of generating successful batches again. The API's
`GET /api/v1/trips/{id}/progress` reads the workflow stage; the frontend shows
that stage, a progress bar and elapsed time while polling. The planning model is
unchanged. City headings and highlights appear directly before that city's days.

Hotel provider queries use a concise city name instead of AI neighborhood prose,
which can cause Google Hotels to return no results. Hotel comparison links open
Google Hotels directly with location, stay dates, guest ages, accommodation type
and the 4+ rating filter encoded in its `ts` search state. This format follows
[SerpApi's Google Hotels search-state analysis](https://serpapi.com/blog/decoding-protobuf-messages-without-schema/).
Room counts and final capacity still need confirmation with the selected property.

Origin autocomplete supports airport names/IATA codes as well as cities, with
aliases for Washington DC/D.C. Destination inputs remain city/country searches
so daily itineraries target a place to explore. Airport suggestions use the
MIT-licensed airportsdata 20260905 extract; its license is in `apps/web/src/data`.

Flight alternatives use Google Flights' encoded route/date/stops state. For
parties above nine travelers, searches show one adult for route exploration and
do not attach a smaller-party quote to the whole group. The UI explains that
the full party needs an airline/group quote. Airbnb searches use `/s/homes` with
an explicit location query, dates, guest count and entire-home filter.
Edit/new-trip actions stay disabled until planning completes or fails; editing
does not cancel a running Temporal workflow.
