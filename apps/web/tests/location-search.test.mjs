import assert from "node:assert/strict";
import test from "node:test";
import { searchLocations } from "../src/lib/location-search.ts";

test("partial city names rank familiar cities first", () => {
  assert.equal(searchLocations("tok", true)[0].label, "Tokyo, Japan");
  assert.equal(searchLocations("lond", true)[0].label, "London, United Kingdom");
});
test("country selection is available for destinations and excluded for origins", () => {
  assert.equal(searchLocations("Japan")[0].kind, "country");
  assert.equal(searchLocations("Japan")[0].label, "Japan");
  assert.ok(searchLocations("Japan", true).every(item => item.kind === "city"));
});
test("search is accent insensitive and supports city plus country", () => {
  assert.match(searchLocations("sao paulo", true)[0].label, /São Paulo/);
  assert.equal(searchLocations("Tokyo Japan", true)[0].label, "Tokyo, Japan");
});
test("results are bounded, distinct and support an empty search", () => {
  assert.ok(searchLocations("").length > 0);
  const results = searchLocations("san");
  assert.ok(results.length <= 10);
  assert.equal(new Set(results.map(item => item.label)).size, results.length);
  assert.equal(searchLocations("x").length, 0);
});
test("ambiguous city names include regions where appropriate", () => {
  const results = searchLocations("Springfield United States", true);
  assert.ok(results.length > 1);
  assert.ok(results.every(item => item.label.split(",").length >= 3));
});

test("Washington DC aliases work without the formal region name", () => {
  for (const query of ["Washington DC", "Washington D.C.", "WashingtonDC"]) {
    assert.equal(searchLocations(query, true, true)[0].label, "Washington, District of Columbia, United States");
  }
});

test("origins can search airports by code, airport name or city", () => {
  assert.equal(searchLocations("IAD", true, true)[0].value, "IAD");
  assert.ok(searchLocations("Dulles", true, true).some(item => item.value === "IAD"));
  assert.ok(searchLocations("Washington DC", true, true).some(item => item.kind === "airport"));
  assert.ok(searchLocations("IAD", true).every(item => item.kind !== "airport"));
});
