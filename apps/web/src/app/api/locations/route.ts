import { searchLocations } from "@/lib/location-search";

export function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const query = params.get("q") ?? "";
  if (query.length > 80)
    return Response.json(
      { detail: "Location searches must be 80 characters or fewer" },
      { status: 400 },
    );
  return Response.json({
    locations: searchLocations(query, params.get("citiesOnly") === "true"),
  });
}
