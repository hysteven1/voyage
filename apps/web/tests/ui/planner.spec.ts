import { expect, test, type Page } from "@playwright/test";
import type { TripForm } from "../../src/lib/trip";

async function chooseDates(page: Page) {
  await page.getByRole("button", { name: /choose your travel dates/i }).click();
  const calendar = page.getByRole("dialog");
  await calendar
    .getByRole("gridcell", { name: "November 2, 2026", exact: true })
    .click();
  await expect(
    calendar.getByRole("gridcell", { name: "November 1, 2026", exact: true }),
  ).toBeDisabled();
  await calendar
    .getByRole("gridcell", { name: "November 8, 2026", exact: true })
    .click();
  await expect(
    calendar.getByRole("gridcell", { name: "November 2, 2026", exact: true }),
  ).toHaveAttribute("aria-description", "Start date");
  await expect(
    calendar.getByRole("gridcell", { name: "November 8, 2026", exact: true }),
  ).toHaveAttribute("aria-description", "End date");
  await expect(
    calendar.getByRole("gridcell", { name: "November 5, 2026", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await expect(
    calendar
      .getByRole("gridcell", { name: "November 5, 2026", exact: true })
      .locator(".."),
  ).toHaveCSS("background-color", "rgb(227, 238, 229)");
  await calendar.getByRole("button", { name: "Use these dates" }).click();
  await expect(calendar).not.toBeVisible();
  await expect(page.getByText("Nov 2, 2026", { exact: true })).toBeVisible();
  await expect(page.getByText("Nov 8, 2026", { exact: true })).toBeVisible();
  await expect(page.getByText(/nights of possibility/)).toHaveCount(0);
}
async function selectLocation(
  page: Page,
  label: string,
  query: string,
  suggestion: string,
) {
  const input = page.getByRole("combobox", { name: label, exact: true });
  await input.fill(query);
  await page
    .getByRole("option", { name: new RegExp(suggestion) })
    .first()
    .click();
  await expect(input).toHaveValue(suggestion);
}

async function mockPlanner(
  page: Page,
  withOffers = false,
  searchUnavailable = false,
  partial = false,
) {
  const captured: {
    proposal?: TripForm;
    created?: TripForm;
    starts: number;
  } = { starts: 0 };
  await page.route("**/api/v1/trips/route-proposal", async (route) => {
    const input = route.request().postDataJSON();
    captured.proposal = input;
    input.options.route[0] = {
      ...input.options.route[0],
      nights: 6,
      travel_days: 0,
      mode: "flight",
      flight_preferences: {
        ...input.options.flight_preferences,
        latest_arrival: null,
      },
    };
    input.options.return_travel_days = 0;
    await route.fulfill({
      json: {
        options: input.options,
        assumptions: [],
        conflicts: [],
        source: "offline_estimates",
      },
    });
  });
  await page.route("**/api/v1/trips", async (route) => {
    captured.created = route.request().postDataJSON();
    await route.fulfill({ json: { id: "test-trip" } });
  });
  await page.route("**/api/v1/trips/test-trip/plan", async (route) => {
    captured.starts++;
    await route.fulfill({ json: { status: "planning" } });
  });
  await page.route("**/api/v1/trips/test-trip", (route) =>
    route.fulfill({ json: { status: "completed" } }),
  );
  await page.route("**/api/v1/trips/test-trip/itinerary", (route) =>
    route.fulfill({
      json: {
        version: 2,
        trip_id: "test-trip",
        currency: "USD",
        travelers: captured.created?.travelers ?? 2,
        route: partial
          ? ["Tokyo, Japan", "Kyoto, Japan", "Osaka, Japan"].map(
              (location) => ({ location }),
            )
          : undefined,
        incomplete_destinations: partial ? ["Kyoto, Japan"] : [],
        data_source: "planning_estimates",
        suggestion_source: "offline_templates",
        narrative: {
          title: partial
            ? "Tokyo, Japan D Kyoto, Japan D Osaka, Japan"
            : "A week in Tokyo",
          summary: "A little exploration, a little breathing room.",
          days: [],
        },
        budget: {
          transport: "0",
          lodging: "660",
          food: "560",
          activities: "150",
          car: "0",
          contingency: "205.50",
          total: "1575.50",
          target: null,
          limit: null,
          remaining: null,
          above_target: null,
          per_person_total: "787.75",
          spending_style: "value",
        },
        destination_highlights:
          withOffers || partial
            ? [
                {
                  location: "Tokyo, Japan",
                  highlights: [
                    {
                      name: "Shibuya Sky",
                      reason: "A broad view of the city skyline.",
                    },
                  ],
                  day_trips: [
                    {
                      name: "Hakone",
                      reason: "Mountains and lakes beyond Tokyo.",
                      travel_minutes: 210,
                    },
                  ],
                },
                ...(partial
                  ? [
                      {
                        location: "Kyoto, Japan",
                        highlights: [
                          {
                            name: "Kiyomizu-dera",
                            reason: "Temple views over Kyoto.",
                          },
                        ],
                        day_trips: [],
                      },
                    ]
                  : []),
              ]
            : [],
        destination_estimates: [
          {
            location: "Tokyo, Japan",
            lodging: "660",
            food: "560",
            activities: "150",
            subtotal: "1370",
          },
        ],
        legs: withOffers
          ? [
              {
                origin: "London, UK",
                destination: "Tokyo, Japan",
                mode: "flight",
                departure_date: "2026-11-02",
                arrival_date: "2026-11-03",
                estimated_hours: 14,
                estimated_cost: "1200",
                search_url: "https://www.google.com/travel/flights?q=fallback",
                alternatives_url:
                  "https://www.google.com/travel/flights?tfs=alternatives",
                restrictions: {
                  max_stops: 0,
                  allow_overnight: true,
                  earliest_departure: null,
                  latest_arrival: null,
                },
                selection_status: searchUnavailable
                  ? "unavailable"
                  : "selected",
                selected_flight: searchUnavailable
                  ? undefined
                  : {
                      airlines: ["Example Air"],
                      flight_numbers: ["EA 123"],
                      departure_airport: "LHR",
                      arrival_airport: "HND",
                      departure_time: "2026-11-02 18:00",
                      arrival_time: "2026-11-03 17:00",
                      departure_timezone: "Europe/London",
                      arrival_timezone: "Asia/Tokyo",
                      departure_timezone_abbreviation: "GMT",
                      arrival_timezone_abbreviation: "JST",
                      stops: 0,
                      price: "1200",
                      google_flights_url:
                        "https://www.google.com/travel/flights?tfs=selected",
                      checked_at: "2026-11-01T14:00:00Z",
                    },
              },
            ]
          : [],
        stays: [
          {
            location: "Tokyo, Japan",
            area: "Central neighborhood",
            check_in: "2026-11-02",
            check_out: "2026-11-08",
            rooms: 1,
            type: "either",
            estimated_cost: "660",
            search_url: "https://www.google.com/search?q=Tokyo+hotels",
            criteria: "Check reviews and transit access.",
            ...(withOffers
              ? {
                  alternatives_url:
                    "https://www.google.com/travel/search?dates=november",
                  rental_alternatives_url:
                    "https://www.airbnb.com/s/Tokyo/homes?checkin=2026-11-02&checkout=2026-11-08",
                  selected_stay: {
                    name: "Example Shinjuku Hotel",
                    rating: 4.6,
                    reviews: 432,
                    quoted_total: "660",
                    booking_url:
                      "https://example.com/reserve?checkin=2026-11-02",
                    capacity_note: "Confirm room quantity and final fees.",
                    checked_at: "2026-11-01T14:00:00Z",
                  },
                }
              : {}),
          },
          ...(partial
            ? [
                {
                  location: "Kyoto, Japan",
                  area: "Kyoto Station",
                  check_in: "2026-11-03",
                  check_out: "2026-11-08",
                  rooms: 1,
                  type: "hotel",
                  estimated_cost: "100",
                  search_url: "https://www.google.com/travel/search?q=Kyoto",
                  criteria: "Near transit",
                },
              ]
            : []),
        ],
        rental_car: null,
        days: [
          {
            date: "2026-11-02",
            location: "Tokyo, Japan",
            area: "Central neighborhood",
            kind: "arrival",
            activities: [
              {
                id: "walk",
                name: withOffers
                  ? "Hachiko statue"
                  : "An easy neighborhood walk",
                area: "Central neighborhood",
                price_per_person: "0",
                duration_hours: 1,
                ...(withOffers
                  ? {
                      duration_minutes: 5,
                      must_see: true,
                      reason: "A brief stop at a beloved Tokyo landmark.",
                    }
                  : {}),
                search_url: "https://www.google.com/search?q=Tokyo+walks",
              },
            ],
            rain_alternative: null,
          },
          ...(partial
            ? [
                {
                  date: "2026-11-03",
                  location: "Kyoto, Japan",
                  title: "Activity recommendations unavailable",
                  kind: "full",
                  needs_personalization: true,
                  activities: [],
                  rain_alternative: null,
                },
              ]
            : []),
        ],
        assumptions: [],
        notes: "",
        accessibility: "",
      },
    }),
  );
  return captured;
}

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(new Date("2026-11-01T14:00:00Z"));
  await page.goto("/");
});

test("origin search accepts Washington DC and specific airport codes", async ({
  page,
}) => {
  const origin = page.getByRole("combobox", { name: "From", exact: true });
  await origin.fill("Washington DC");
  await expect(
    page
      .getByRole("option", {
        name: /Washington, District of Columbia, United States/,
      })
      .first(),
  ).toBeVisible();
  await origin.fill("IAD");
  await page.getByRole("option", { name: /\(IAD\)/ }).click();
  await expect(origin).toHaveValue("IAD");
});

test("polished fields, live route summary, and aligned destination controls", async ({
  page,
}, info) => {
  await expect(
    page.getByRole("banner").getByRole("link", { name: "Plan a trip" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("banner").getByText("Less planning. A lot more living."),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Remove destination/ }),
  ).toHaveCount(0);
  const from = page.getByRole("combobox", { name: "From", exact: true });
  const centers = await from.evaluate((input) => {
    const form = input.closest(".MuiFormControl-root")!;
    const label = form
      .querySelector(".MuiInputLabel-root")!
      .getBoundingClientRect();
    const field = form
      .querySelector(".MuiOutlinedInput-root")!
      .getBoundingClientRect();
    return {
      distance: Math.abs(
        label.y + label.height / 2 - field.y - field.height / 2,
      ),
      height: field.height,
    };
  });
  expect(centers.distance).toBeLessThan(3);
  expect(centers.height).toBeGreaterThanOrEqual(56);
  await selectLocation(page, "From", "tok", "Tokyo, Japan");
  await page
    .getByRole("heading", { name: "Let’s put a pin in the map." })
    .click();
  await from.click();
  expect(
    await from.evaluate(
      (input) =>
        (input as HTMLInputElement).selectionStart ===
        (input as HTMLInputElement).selectionEnd,
    ),
  ).toBeTruthy();
  await expect(from).toHaveCSS("outline-style", "none");
  const where = page.getByRole("combobox", { name: "Where to?", exact: true });
  await where.fill("kyo");
  await expect(
    page.getByRole("option", { name: /Kyoto, Japan/ }),
  ).toBeVisible();
  await where.press("Enter");
  await expect(where).toHaveValue("Kyoto, Japan");
  if (info.project.name === "desktop") {
    await expect(page.getByRole("complementary")).toContainText(
      "Tokyo, Japan → Kyoto, Japan",
    );
    await expect(page.getByRole("complementary")).not.toContainText(/budget/i);
  }
  await page.getByRole("button", { name: "Add another stop" }).click();
  await expect(
    page.getByRole("combobox", { name: "Destination 1", exact: true }),
  ).toHaveValue("Kyoto, Japan");
  await expect(
    page.getByText("Search or enter a city or country."),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: /Remove destination/ }),
  ).toHaveCount(2);
  const alignment = await page
    .getByRole("button", { name: "Remove destination 1" })
    .evaluate((button) => {
      const field = button
        .closest(".destination-row")!
        .querySelector(".MuiOutlinedInput-root")!
        .getBoundingClientRect();
      const icon = button.getBoundingClientRect();
      return Math.abs(field.y + field.height / 2 - icon.y - icon.height / 2);
    });
  expect(alignment).toBeLessThan(2);
  await page.getByRole("button", { name: "Remove destination 2" }).click();
  await expect(
    page.getByRole("button", { name: /Remove destination/ }),
  ).toHaveCount(0);
  await chooseDates(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({
    path: `/tmp/voyage-${info.project.name}-polished.png`,
    fullPage: true,
    animations: "disabled",
  });
});

test("already-there hides origin, offers an optional budget, and generates in two steps", async ({
  page,
}) => {
  await page
    .getByRole("combobox", { name: "From", exact: true })
    .fill("London, UK");
  await page.getByRole("button", { name: /Already there/ }).click();
  await expect(page.getByRole("combobox", { name: /From/ })).toHaveCount(0);
  await selectLocation(page, "Where", "tok", "Tokyo, Japan");
  await chooseDates(page);
  await page.getByRole("button", { name: "Make it personal" }).click();
  await expect(
    page.getByRole("heading", {
      name: "What would you love to explore? (optional)",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Relaxation", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Food", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: /Good value/ }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(
    page.getByRole("spinbutton", {
      name: "Target per person · USD (optional)",
    }),
  ).toHaveValue("");
  const captured = await mockPlanner(page);
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(
    page.getByRole("heading", { name: "A week in Tokyo" }),
  ).toBeVisible();
  expect(captured.created?.origin).toBeNull();
  expect(captured.created?.budget).toBeNull();
  expect(captured.created?.options.endpoint).toBe("one_way");
  expect(captured.created?.options.spending_style).toBe("value");
  expect(captured.starts).toBe(1);
  await expect(page.getByText(/Maximum:/)).toHaveCount(0);
  await expect(page.getByText(/without a spending target/)).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});

test("flight departure window applies to leaving home and arrival window survives the return", async ({
  page,
}) => {
  await page
    .getByRole("combobox", { name: "From", exact: true })
    .fill("London, UK");
  await page
    .getByRole("combobox", { name: "Where to?", exact: true })
    .fill("Tokyo, Japan");
  await page.getByRole("radio", { name: "Nonstop only", exact: true }).check();
  await expect(
    page.getByRole("radiogroup", { name: "Overnight flights" }),
  ).toHaveCount(0);
  await page.getByLabel("Leave home after (optional)").fill("17:00");
  await page.getByLabel("Get home by (optional)").fill("20:00");
  await chooseDates(page);
  await page.getByRole("button", { name: "Make it personal" }).click();
  await page
    .getByRole("spinbutton", { name: "Target per person · USD (optional)" })
    .fill("1500");
  const captured = await mockPlanner(page);
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(
    page.getByRole("heading", { name: "A week in Tokyo" }),
  ).toBeVisible();
  expect(captured.created?.budget).toBe(1500);
  expect(captured.created?.options.budget_basis).toBe("per_person");
  expect(captured.created?.options.budget_enforcement).toBe("target");
  const preferences = {
    departure_scope: "first_flight",
    arrival_scope: "return_home",
    max_stops: 0,
    allow_overnight: true,
    earliest_departure: "17:00",
    latest_arrival: null,
  };
  expect(captured.created?.options.route[0].flight_preferences).toEqual(
    preferences,
  );
  expect(captured.created?.options.return_flight_preferences).toEqual({
    ...preferences,
    earliest_departure: null,
    latest_arrival: "20:00",
  });
});

test("group budgets, optional child ages and automatic hotel room counts", async ({
  page,
}) => {
  await page.getByRole("button", { name: /Road trip/ }).click();
  await expect(
    page.getByRole("radiogroup", { name: "Connections" }),
  ).toHaveCount(0);
  await page
    .getByRole("combobox", { name: "From", exact: true })
    .fill("London, UK");
  await page
    .getByRole("combobox", { name: "Where to?", exact: true })
    .fill("Paris, France");
  await chooseDates(page);
  await page.getByRole("button", { name: "Make it personal" }).click();
  await page.getByRole("combobox", { name: "Budget for" }).click();
  await page.getByRole("option", { name: "Whole group", exact: true }).click();
  await page
    .getByRole("spinbutton", { name: "Group target · USD (optional)" })
    .fill("4000");
  await page.getByRole("button", { name: /Budget conscious/ }).click();
  await expect(
    page.getByRole("combobox", { name: "Where do you like to stay?" }),
  ).toHaveCount(0);
  await expect(page.getByLabel("I’m interested in renting a car")).toHaveCount(
    0,
  );
  for (let i = 0; i < 3; i++)
    await page
      .getByRole("button", { name: "Increase adults", exact: true })
      .click();
  for (let i = 0; i < 4; i++)
    await page
      .getByRole("button", { name: "Increase children", exact: true })
      .click();
  await expect(
    page.getByText(/Some airlines offer lower fares for children/),
  ).toBeVisible();
  await expect(
    page.getByRole("combobox", { name: "Child 1 age (optional)" }),
  ).toBeVisible();
  await expect(
    page.getByRole("status", { name: "Rooms", exact: true }),
  ).toHaveText("3");
  const captured = await mockPlanner(page);
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(
    page.getByRole("heading", { name: "A week in Tokyo" }),
  ).toBeVisible();
  expect(captured.created?.options.budget_basis).toBe("group");
  expect(captured.created?.options.spending_style).toBe("budget");
  expect(captured.created?.options.lodging).toBe("hotel");
  expect(captured.created?.options.rental_car).toBe(false);
  expect(captured.created?.options.children).toBe(4);
  expect(captured.created?.options.child_ages).toEqual([]);
  expect(captured.created?.travelers).toBe(9);
  expect(captured.created?.preferences).toEqual([]);
});

test("manual entry survives unavailable suggestions and validation clears after correction", async ({
  page,
}) => {
  await page.route("**/api/locations?**", (route) =>
    route.fulfill({ status: 503, json: {} }),
  );
  const from = page.getByRole("combobox", { name: "From", exact: true });
  await from.fill("Somewhere quiet");
  await expect(
    page.getByText("Suggestions unavailable. You can still enter a location."),
  ).toBeVisible();
  await from.press("Tab");
  await expect(from).toHaveValue("Somewhere quiet");
  await page
    .getByRole("combobox", { name: "Where to?", exact: true })
    .fill("Tokyo, Japan");
  await page.getByRole("button", { name: "Make it personal" }).click();
  const dates = page.getByRole("button", { name: /choose your travel dates/i });
  await expect(dates).toHaveAttribute("aria-invalid", "true");
  await expect(page.locator('.planner-card [role="alert"]')).toHaveCount(0);
  await chooseDates(page);
  await expect(
    page.getByRole("button", { name: /Nov 2, 2026 — Nov 8, 2026/ }),
  ).toHaveAttribute("aria-invalid", "false");
});

test("a cross-month date range remains highlighted when reopened and clears correctly", async ({
  page,
}, info) => {
  await page.getByRole("button", { name: /choose your travel dates/i }).click();
  const calendar = page.getByRole("dialog");
  await calendar
    .getByRole("gridcell", { name: "November 2, 2026", exact: true })
    .click();
  await calendar.getByRole("button", { name: "Next month" }).click();
  await calendar
    .getByRole("gridcell", { name: "December 8, 2026", exact: true })
    .click();
  await expect(
    calendar.getByRole("gridcell", { name: "December 5, 2026", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await calendar.getByRole("button", { name: "Use these dates" }).click();
  await expect(calendar).not.toBeVisible();
  await page.getByRole("button", { name: /Nov 2, 2026 — Dec 8, 2026/ }).click();
  await expect(
    calendar.getByRole("gridcell", { name: "November 2, 2026", exact: true }),
  ).toHaveAttribute("aria-description", "Start date");
  await calendar.getByRole("button", { name: /Return.*Dec 8/ }).click();
  await expect(
    calendar.getByRole("gridcell", { name: "December 8, 2026", exact: true }),
  ).toHaveAttribute("aria-description", "End date");
  await page.screenshot({
    path: `/tmp/voyage-${info.project.name}-date-range.png`,
    animations: "disabled",
  });
  await calendar.getByRole("button", { name: "Clear dates" }).click();
  await expect(calendar.getByRole("gridcell", { selected: true })).toHaveCount(
    0,
  );
  await expect(
    calendar.getByRole("button", { name: "Use these dates" }),
  ).toBeDisabled();
});

test("Next highlights missing fields together and clears red borders when corrected", async ({
  page,
}) => {
  const from = page.getByRole("combobox", { name: "From", exact: true });
  const where = page.getByRole("combobox", { name: "Where to?", exact: true });
  const dates = page.getByRole("button", { name: /choose your travel dates/i });
  await expect(from).toHaveAttribute("aria-invalid", "false");
  await page.getByRole("button", { name: "Make it personal" }).click();
  await expect(from).toHaveAttribute("aria-invalid", "true");
  await expect(where).toHaveAttribute("aria-invalid", "true");
  await expect(dates).toHaveAttribute("aria-invalid", "true");
  await expect(dates).toHaveCSS("border-top-color", "rgb(180, 64, 61)");
  await expect(page.locator('.planner-card [role="alert"]')).toHaveCount(0);
  await from.fill("London, UK");
  await where.fill("Tokyo, Japan");
  await expect(from).toHaveAttribute("aria-invalid", "false");
  await expect(where).toHaveAttribute("aria-invalid", "false");
  await chooseDates(page);
  await page.getByRole("button", { name: "Make it personal" }).click();
  const budget = page.getByRole("spinbutton", {
    name: "Target per person · USD (optional)",
  });
  await budget.fill("-1");
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(budget).toHaveAttribute("aria-invalid", "true");
  await budget.fill("");
  await expect(budget).toHaveAttribute("aria-invalid", "false");
});

test("clicking either time field opens the native picker without using its clock icon", async ({
  page,
}) => {
  await page.evaluate(() => {
    const nativePicker = HTMLInputElement.prototype.showPicker;
    HTMLInputElement.prototype.showPicker = function () {
      nativePicker.call(this);
      this.dataset.pickerOpened = "true";
    };
  });
  for (const label of [
    "Leave home after (optional)",
    "Get home by (optional)",
  ]) {
    const input = page.getByLabel(label);
    await input.locator("..").click({ position: { x: 20, y: 12 } });
    await expect(input).toHaveAttribute("data-picker-opened", "true");
    await page.keyboard.press("Escape");
  }
});

test("selected travel options follow the budget with specific and alternative links", async ({
  page,
}) => {
  await page
    .getByRole("combobox", { name: "From", exact: true })
    .fill("London, UK");
  await page
    .getByRole("combobox", { name: "Where to?", exact: true })
    .fill("Tokyo, Japan");
  await chooseDates(page);
  await page.getByRole("button", { name: "Make it personal" }).click();
  await page.getByRole("button", { name: "Theme parks", exact: true }).click();
  await page.getByRole("button", { name: "Day trips", exact: true }).click();
  const captured = await mockPlanner(page, true);
  await page.getByRole("button", { name: "Plan my trip" }).click();
  const budget = page.getByText("Estimated for the group · USD", {
    exact: true,
  });
  const flights = page.getByRole("heading", {
    name: "Getting from here to there.",
  });
  const stays = page.getByRole("heading", {
    name: "Somewhere to call home, for a while.",
  });
  const days = page.getByRole("heading", {
    name: "Your days, with room to wander.",
  });
  await expect(days).toBeVisible();
  await expect(
    page.getByText("LHR Nov 2, 18:00 GMT → HND Nov 3, 17:00 JST", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByText(/Confirm in search:/)).toHaveCount(0);
  await expect(page.getByText(/estimated for the group/)).toHaveCount(0);
  await expect(page.getByText(/estimated stay total/)).toHaveCount(0);
  await expect(
    page.getByText("Check reviews and transit access.", { exact: true }),
  ).toHaveCount(0);
  expect(captured.created?.preferences).toEqual(["Theme parks", "Day trips"]);
  await expect(
    page.getByRole("heading", { name: "Highlights in Tokyo, Japan" }),
  ).toBeVisible();
  await expect(
    page.getByText("A broad view of the city skyline."),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Day trips worth considering" })
    .click();
  await expect(
    page.getByText("Mountains and lakes beyond Tokyo."),
  ).toBeVisible();
  await expect(
    page.getByText("About 3h 30 min round-trip travel", { exact: true }),
  ).toBeVisible();
  for (const [before, after] of [
    [budget, flights],
    [flights, stays],
    [stays, days],
  ]) {
    const next = await after.elementHandle();
    expect(
      await before.evaluate(
        (node, other) =>
          Boolean(
            node.compareDocumentPosition(other!) &
            Node.DOCUMENT_POSITION_FOLLOWING,
          ),
        next,
      ),
    ).toBe(true);
  }
  await expect(
    page.getByRole("link", { name: "View selected flight on Google Flights" }),
  ).toHaveAttribute(
    "href",
    "https://www.google.com/travel/flights?tfs=selected",
  );
  await expect(
    page.getByRole("link", { name: /Other flights.*nonstop/ }),
  ).toHaveAttribute(
    "href",
    "https://www.google.com/travel/flights?tfs=alternatives",
  );
  await expect(
    page.getByText("Example Shinjuku Hotel", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "View recommended stay" }),
  ).toHaveAttribute("href", "https://example.com/reserve?checkin=2026-11-02");
  await expect(
    page.getByRole("link", { name: "Other hotels for your dates" }),
  ).toHaveAttribute(
    "href",
    "https://www.google.com/travel/search?dates=november",
  );
  await expect(
    page.getByRole("link", { name: "Explore entire homes on Airbnb" }),
  ).toHaveAttribute("href", /checkin=2026-11-02/);
  await expect(
    page.locator(".activity-row").filter({ hasText: "Hachiko statue" }),
  ).toContainText("About 5 min");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});

test("old section fragments return to the clean home URL", async ({ page }) => {
  await page.goto("/#how-it-works");
  await expect(page).toHaveURL(/\/$/);
  await expect(
    page.getByRole("combobox", { name: "From", exact: true }),
  ).toBeVisible();
});

test("a failed live search is distinguished from no matching flights", async ({
  page,
}) => {
  await page
    .getByRole("combobox", { name: "From", exact: true })
    .fill("Washington, District of Columbia, United States");
  await page
    .getByRole("combobox", { name: "Where to?", exact: true })
    .fill("Tokyo, Japan");
  await chooseDates(page);
  await page.getByRole("button", { name: "Make it personal" }).click();
  await mockPlanner(page, true, true);
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(
    page.getByText(/The live flight search was unavailable/),
  ).toBeVisible();
  await expect(
    page.getByText(/no options matching these preferences/),
  ).toHaveCount(0);
});

test("itinerary actions distinguish editing current details from starting fresh", async ({
  page,
}) => {
  await page
    .getByRole("combobox", { name: "From", exact: true })
    .fill("London, UK");
  await page
    .getByRole("combobox", { name: "Where to?", exact: true })
    .fill("Tokyo, Japan");
  await chooseDates(page);
  await page.getByRole("button", { name: "Make it personal" }).click();
  await mockPlanner(page);
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(
    page.getByRole("heading", { name: "A week in Tokyo" }),
  ).toBeVisible();
  await expect(page.getByText(/Your details are saved/)).toHaveCount(0);
  await page.getByRole("button", { name: "Edit trip details" }).click();
  await expect(
    page.getByRole("combobox", { name: "From", exact: true }),
  ).toHaveValue("London, UK");
  await expect(
    page.getByRole("combobox", { name: "Where to?", exact: true }),
  ).toHaveValue("Tokyo, Japan");
  await page.getByRole("button", { name: "Make it personal" }).click();
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(
    page.getByRole("heading", { name: "A week in Tokyo" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Plan another trip" }).click();
  await expect(
    page.getByRole("combobox", { name: "From", exact: true }),
  ).toHaveValue("");
  await expect(
    page.getByRole("combobox", { name: "Where to?", exact: true }),
  ).toHaveValue("");
});

test("refresh starts a new session without reopening previous trips", async ({
  page,
}) => {
  await page.getByRole("button", { name: /Already there/ }).click();
  await page
    .getByRole("combobox", { name: "Where", exact: true })
    .fill("Tokyo, Japan");
  await chooseDates(page);
  await page.getByRole("button", { name: "Make it personal" }).click();
  const captured = await mockPlanner(page);
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(
    page.getByRole("heading", { name: "A week in Tokyo" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("combobox", { name: "From", exact: true }),
  ).toHaveValue("");
  await expect(
    page.getByRole("heading", { name: "A week in Tokyo" }),
  ).toHaveCount(0);
  expect(captured.starts).toBe(1);
});

test("legacy partial suggestions keep a clean route title without the removed warning", async ({
  page,
}) => {
  await page.getByRole("button", { name: /Already there/ }).click();
  await page
    .getByRole("combobox", { name: "Where", exact: true })
    .fill("Tokyo, Japan");
  await chooseDates(page);
  await page.getByRole("button", { name: "Make it personal" }).click();
  await mockPlanner(page, false, false, true);
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(
    page.getByRole("heading", {
      name: "Tokyo, Japan → Kyoto, Japan → Osaka, Japan",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByText("Tokyo, Japan D Kyoto, Japan D Osaka, Japan", {
      exact: true,
    }),
  ).toHaveCount(0);
  await expect(
    page.getByText(/Activity recommendations could not be completed for/),
  ).toHaveCount(0);
  await expect(
    page.getByText("Partial trip estimate · USD", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(/No placeholder activities or visit costs have been added/),
  ).toBeVisible();
  await expect(
    page
      .getByRole("region", { name: "Days in Kyoto, Japan" })
      .getByRole("heading", { name: "Kyoto, Japan", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Highlights in Kyoto, Japan" }),
  ).toBeVisible();
  expect(
    await page
      .getByRole("heading", { name: "Highlights in Kyoto, Japan" })
      .evaluate(
        (element) =>
          !!(
            element.compareDocumentPosition(
              document.querySelectorAll(".day-heading")[1],
            ) & Node.DOCUMENT_POSITION_FOLLOWING
          ),
      ),
  ).toBe(true);
  await expect(
    page.getByText("The details behind your plan", { exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: "An easy neighborhood walk" }),
  ).toHaveCount(0);
});

test("planning shows live workflow stages before the itinerary is ready", async ({
  page,
}) => {
  await page.getByRole("button", { name: /Already there/ }).click();
  await page
    .getByRole("combobox", { name: "Where", exact: true })
    .fill("Tokyo, Japan");
  await chooseDates(page);
  await page.getByRole("button", { name: "Make it personal" }).click();
  await mockPlanner(page);
  let complete = false;
  await page.route("**/api/v1/trips/test-trip", (route) =>
    route.fulfill({ json: { status: complete ? "completed" : "planning" } }),
  );
  await page.route("**/api/v1/trips/test-trip/progress", (route) =>
    route.fulfill({
      json: {
        stage: "travel",
        label: "Finding flights and places to stay",
        percent: 75,
      },
    }),
  );
  await page.getByRole("button", { name: "Plan my trip" }).click();
  await expect(
    page.getByText("Finding flights and places to stay", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("progressbar", { name: "Trip planning progress" }),
  ).toHaveAttribute("aria-valuenow", "75");
  await expect(
    page.getByRole("button", { name: "Edit trip details", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Plan another trip", exact: true }),
  ).toBeDisabled();
  complete = true;
  await expect(
    page.getByRole("region", { name: "Your itinerary" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Edit trip details", exact: true }),
  ).toBeEnabled();
});
