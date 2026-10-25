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
