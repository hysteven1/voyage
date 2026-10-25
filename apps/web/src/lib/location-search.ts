// Server-only dataset: never import this module from a client component.
// GeoNames via cities.json, CC BY 4.0. Attribution is displayed in the site footer.
import cities from "cities.json" with { type: "json" };
import regions from "cities.json/admin1" with { type: "json" };

export type LocationSuggestion = {
  id: string;
  label: string;
  detail: string;
  kind: "city" | "country";
};
const countryNames = new Intl.DisplayNames(["en"], { type: "region" });
const regionNames = new Map(
  regions.map((region) => [region.code, region.name]),
);
const normalize = (text: string) =>
  text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
const popular = [
  "Tokyo",
  "London",
  "Paris",
  "New York City",
  "Rome",
  "Kyoto",
  "Bangkok",
  "Barcelona",
  "Seoul",
  "Sydney",
  "Lisbon",
  "Amsterdam",
  "Singapore",
  "Dubai",
  "Istanbul",
  "Mexico City",
  "Cape Town",
  "Los Angeles",
  "San Francisco",
  "Madrid",
  "Berlin",
  "Osaka",
  "Toronto",
  "Vancouver",
  "Melbourne",
  "Mumbai",
  "Delhi",
  "São Paulo",
  "Buenos Aires",
  "Cairo",
];
const popularity = new Map(
  popular.map((name, i) => [normalize(name), popular.length - i]),
);
const preferredCountries: Record<string, string> = {
  tokyo: "JP",
  london: "GB",
  paris: "FR",
  "new york city": "US",
  rome: "IT",
  kyoto: "JP",
  bangkok: "TH",
  barcelona: "ES",
  seoul: "KR",
  sydney: "AU",
  lisbon: "PT",
  amsterdam: "NL",
  singapore: "SG",
  dubai: "AE",
  istanbul: "TR",
  "mexico city": "MX",
  "cape town": "ZA",
  "los angeles": "US",
  "san francisco": "US",
  madrid: "ES",
  berlin: "DE",
  osaka: "JP",
  toronto: "CA",
  vancouver: "CA",
  melbourne: "AU",
  mumbai: "IN",
  delhi: "IN",
  "sao paulo": "BR",
  "buenos aires": "AR",
  cairo: "EG",
};
const countryAliases: Record<string, string> = {
  US: "USA America",
  GB: "UK Britain England",
  AE: "UAE",
  KR: "Korea",
};
const entries = cities.map((city) => {
  const country = countryNames.of(city.country) ?? city.country;
  const region = regionNames.get(`${city.country}.${city.admin1}`);
  const label = [
    city.name,
    ...(["US", "CA", "AU"].includes(city.country) &&
    region &&
    region !== city.name
      ? [region]
      : []),
    country,
  ].join(", ");
  return {
    id: `${city.country}:${city.lat}:${city.lng}`,
    label,
    detail: [region, country].filter(Boolean).join(", "),
    kind: "city" as const,
    popularity:
      preferredCountries[normalize(city.name)] === city.country
        ? (popularity.get(normalize(city.name)) ?? 0)
        : 0,
    name: normalize(city.name),
    search: normalize(`${label} ${region ?? ""} ${city.country}`),
  };
});
const countries = [...new Set(cities.map((city) => city.country))].map(
  (code) => {
    const name = countryNames.of(code) ?? code;
    return {
      id: code,
      label: name,
      detail: "Country · we’ll suggest a city to start",
      kind: "country" as const,
      popularity: 0,
      name: normalize(name),
      search: normalize(`${name} ${code} ${countryAliases[code] ?? ""}`),
    };
  },
);

export function searchLocations(
  input: string,
  citiesOnly = false,
): LocationSuggestion[] {
  const query = normalize(input.slice(0, 80));
  if (query.length === 1) return [];
  const tokens = query.split(" ").filter(Boolean);
  const matches = (citiesOnly ? entries : [...countries, ...entries]).filter(
    (entry) =>
      !query
        ? entry.popularity > 0
        : tokens.every((token) => entry.search.includes(token)),
  );
  const score = (entry: (typeof matches)[number]) =>
    (entry.name === query ? 10000 : entry.name.startsWith(query) ? 1000 : 0) +
    (entry.name.startsWith(query) && entry.popularity > 0 ? 20000 : 0) +
    entry.popularity;
  matches.sort((a, b) => score(b) - score(a) || a.label.localeCompare(b.label));
  const seen = new Set<string>();
  return matches
    .filter((entry) => {
      if (seen.has(entry.label)) return false;
      seen.add(entry.label);
      return true;
    })
    .slice(0, 10)
    .map(({ id, label, detail, kind }) => ({ id, label, detail, kind }));
}
