import { expect, test, type Page } from "@playwright/test";

async function chooseDates(page: Page) {
  await page.getByRole("button", { name: /choose your travel dates/i }).click();
  const calendar = page.getByRole("dialog");
  await expect(calendar).toBeVisible();
  await calendar.getByRole("gridcell", { name: "2", exact: true }).click();
  await expect(
    calendar.getByRole("gridcell", { name: "1", exact: true }),
  ).toBeDisabled();
  await calendar.getByRole("gridcell", { name: "8", exact: true }).click();
  await calendar.getByRole("button", { name: "Use these dates" }).click();
  await expect(calendar).not.toBeVisible();
  await expect(
    page.getByText("Nov 2, 2026 — Nov 8, 2026", { exact: true }),
  ).toBeVisible();
}

async function selectLocation(
  page: Page,
  label: string,
  query: string,
  suggestion: string,
) {
  const field = page.getByRole("combobox", { name: label, exact: true });
  await field.fill(query);
  await page
    .getByRole("option", { name: new RegExp(suggestion) })
    .first()
    .click();
  await expect(field).toHaveValue(suggestion);
}

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(new Date("2026-11-01T14:00:00Z"));
  await page.goto("/");
});

test("locations autocomplete, calendar dates, and mobile layout", async ({
  page,
}, testInfo) => {
  await selectLocation(page, "From", "tok", "Tokyo, Japan");
  const destination = page.getByRole("combobox", {
    name: "Where to?",
    exact: true,
  });
  await destination.fill("kyo");
  await expect(
    page.getByRole("option", { name: /Kyoto, Japan/ }),
  ).toBeVisible();
  await destination.press("Enter");
  // Auto-highlight + keyboard navigation must select a real suggestion.
  await expect(destination).toHaveValue("Kyoto, Japan");
  await chooseDates(page);
  await expect(page.getByText("End of journey", { exact: true })).toHaveCount(
    0,
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({
    animations: "disabled",
    path: `/tmp/voyage-${testInfo.project.name}-planner.png`,
    fullPage: true,
  });
  await page.getByRole("button", { name: "Make it personal" }).click();
  await expect(
    page.getByRole("heading", {
      name: "What does your perfect trip feel like?",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Who’s coming along?" }),
  ).toBeVisible();
  for (let i = 0; i < 3; i++)
    await page
      .getByRole("button", { name: "Increase adults", exact: true })
      .click();
  await expect(
    page.getByRole("status", { name: "Rooms", exact: true }),
  ).toHaveText("2");
});

test("already-there trips omit origin and preserve the new default through saving", async ({
  page,
}) => {
  await page.getByRole("button", { name: /Already there/ }).click();
  await selectLocation(page, "Where to?", "tok", "Tokyo, Japan");
  await chooseDates(page);
  await page.getByRole("button", { name: "Make it personal" }).click();
  await page.route("**/api/v1/trips/route-proposal", async (route) => {
    const input = route.request().postDataJSON();
    expect(input.origin).toBeNull();
    expect(input.options.endpoint).toBe("one_way");
    expect(input.options.end_location).toBeNull();
    input.options.route[0] = {
      ...input.options.route[0],
      nights: 6,
      travel_days: 0,
      mode: "train",
    };
    await route.fulfill({
      json: {
        options: input.options,
        assumptions: ["Confirm local details"],
        conflicts: [],
        source: "offline_estimates",
      },
    });
  });
  await page.getByRole("button", { name: "Find my route" }).click();
  await expect(
    page.getByRole("heading", {
      name: "A little fine-tuning. Then, adventure.",
    }),
  ).toBeVisible();
  await expect(
    page.getByText("All 6 nights accounted for. Looking good."),
  ).toBeVisible();
  await page.getByRole("checkbox", { name: /This route feels right/ }).check();
  await page.route("**/api/v1/trips", async (route) => {
    expect(route.request().postDataJSON().options.endpoint).toBe("one_way");
    await route.fulfill({ json: { id: "test-trip" } });
  });
  await page.getByRole("button", { name: "Let’s plan this trip" }).click();
  await expect(
    page.getByRole("heading", { name: "The good part starts here." }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Create my itinerary" }),
  ).toBeVisible();
  await page.route("**/api/v1/trips/test-trip/plan", (route) =>
    route.fulfill({ json: { status: "planning" } }),
  );
  await page.route("**/api/v1/trips/test-trip", (route) =>
    route.fulfill({ json: { status: "completed" } }),
  );
  await page.route("**/api/v1/trips/test-trip/itinerary", (route) =>
    route.fulfill({
      json: {
        version: 2,
        trip_id: "test-trip",
        currency: "USD",
        data_source: "planning_estimates",
        narrative: {
          title: "A week in Tokyo",
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
          target: "3000",
          limit: "3000",
          remaining: "1424.50",
          above_target: "0",
        },
        destination_estimates: [
          {
            location: "Tokyo, Japan",
            lodging: "660",
            food: "560",
            activities: "150",
            subtotal: "1370",
          },
        ],
        legs: [],
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
            criteria: "Check recent reviews and transit access.",
          },
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
                name: "An easy neighborhood walk",
                area: "Central neighborhood",
                price_per_person: "0",
                duration_hours: 1,
                search_url: "https://www.google.com/search?q=Tokyo+walks",
              },
            ],
            rain_alternative: {
              name: "A neighborhood café",
              search_url: "https://www.google.com/search?q=Tokyo+cafes",
            },
          },
        ],
        assumptions: ["Planning estimates, not quotes."],
        notes: "",
        accessibility: "",
        suggestion_source: "offline_templates",
      },
    }),
  );
  await page.getByRole("button", { name: "Create my itinerary" }).click();
  await expect(
    page.getByRole("heading", { name: "A week in Tokyo" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "An easy neighborhood walk" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test("manual locations remain usable when suggestions are unavailable", async ({
  page,
}) => {
  await page.route("**/api/locations?**", (route) =>
    route.fulfill({ status: 503, json: {} }),
  );
  const field = page.getByRole("combobox", { name: "From", exact: true });
  await field.fill("Somewhere quiet");
  await expect(
    page.getByText("Suggestions unavailable. You can still enter a location."),
  ).toBeVisible();
  await field.press("Tab");
  await expect(field).toHaveValue("Somewhere quiet");
});

test("departures require dates and step changes retain typed locations", async ({
  page,
}) => {
  await page
    .getByRole("combobox", { name: "From", exact: true })
    .fill("London, UK");
  await page
    .getByRole("combobox", { name: "Where to?", exact: true })
    .fill("Tokyo, Japan");
  await page.getByRole("button", { name: "Make it personal" }).click();
  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: "Choose departure and return dates" }),
  ).toContainText("Choose departure and return dates");
  await chooseDates(page);
  await page.getByRole("button", { name: "Make it personal" }).click();
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await expect(
    page.getByRole("combobox", { name: "From", exact: true }),
  ).toHaveValue("London, UK");
  await expect(
    page.getByRole("combobox", { name: "Where to?", exact: true }),
  ).toHaveValue("Tokyo, Japan");
});

for (const journey of ["flying", "driving"] as const) {
  test(`${journey} trips default to returning home without an endpoint selector`, async ({
    page,
  }) => {
    if (journey === "driving")
      await page.getByRole("button", { name: /Road trip/ }).click();
    await page
      .getByRole("combobox", { name: "From", exact: true })
      .fill("London, UK");
    await page
      .getByRole("combobox", { name: "Where to?", exact: true })
      .fill("Paris, France");
    await chooseDates(page);
    await page.getByRole("button", { name: "Make it personal" }).click();
    await page.route("**/api/v1/trips/route-proposal", async (route) => {
      const input = route.request().postDataJSON();
      expect(input.options.endpoint).toBe("return");
      expect(input.options.end_location).toBeNull();
      expect(input.options.journey).toBe(journey);
      input.options.route[0] = {
        ...input.options.route[0],
        nights: 6,
        travel_days: 0,
        mode: journey === "driving" ? "drive" : "flight",
      };
      input.options.return_travel_days = 0;
      input.options.return_mode = journey === "driving" ? "drive" : "flight";
      await route.fulfill({
        json: {
          options: input.options,
          source: "offline_estimates",
          assumptions: [],
          conflicts: [],
        },
      });
    });
    await page.getByRole("button", { name: "Find my route" }).click();
    await expect(
      page.getByRole("button", { name: "Back to London, UK" }),
    ).toBeVisible();
  });
}
