export type FlightPreferences = {
  departure_scope?: "all_flights" | "first_flight";
  arrival_scope?: "all_flights" | "return_home";
  max_stops: number;
  earliest_departure: string | null;
  latest_arrival: string | null;
  allow_overnight: boolean;
};
export type Stop = {
  location: string;
  nights: number | null;
  mode: "flight" | "train" | "drive";
  travel_days: number;
  flight_preferences: FlightPreferences | null;
};
export type Options = {
  journey: "flying" | "driving" | "already_there";
  route: Stop[];
  endpoint: "return" | "different" | "one_way";
  end_location: string | null;
  return_mode: "flight" | "train" | "drive";
  return_travel_days: number;
  return_flight_preferences: FlightPreferences | null;
  adults: number;
  child_ages: number[];
  children: number;
  rooms: number;
  accessibility: string;
  budget_basis?: "per_person" | "group";
  spending_style?: "budget" | "value" | "upscale";
  budget_enforcement?: "target" | "ceiling";
  flight_preferences?: FlightPreferences;
  budget_mode: "strict" | "flexible";
  maximum_budget: number | string | null;
  pace: "relaxed" | "balanced" | "busy";
  lodging: "hotel" | "apartment" | "either";
  rental_car: boolean;
  notes: string;
};
export type TripForm = {
  origin: string | null;
  start_date: string;
  end_date: string;
  travelers: number;
  budget: number | null;
  preferences: string[];
  options: Options;
};
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "";
export const flightDefaults: FlightPreferences = {
  departure_scope: "first_flight",
  arrival_scope: "return_home",
  max_stops: 1,
  earliest_departure: null,
  latest_arrival: null,
  allow_overnight: true,
};
export const newStop = (): Stop => ({
  location: "",
  nights: null,
  mode: "train",
  travel_days: 0,
  flight_preferences: null,
});
export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(
    `${API_URL}${path}`,
    body
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : { cache: "no-store" },
  );
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    const detail = result.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((item: { msg: string }) => item.msg).join("; ")
          : `Request failed (${response.status})`,
    );
  }
  return response.json();
}
