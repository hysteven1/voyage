import dayjs from "dayjs";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Chip,
  Divider,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import ExpandMoreRounded from "@mui/icons-material/ExpandMoreRounded";
import NorthEastRounded from "@mui/icons-material/NorthEastRounded";
import FlightTakeoffRounded from "@mui/icons-material/FlightTakeoffRounded";
import HotelRounded from "@mui/icons-material/HotelRounded";
import UmbrellaRounded from "@mui/icons-material/UmbrellaRounded";
import type { FlightPreferences } from "@/lib/trip";

type Activity = {
  id: string;
  name: string;
  area: string;
  price_per_person: string;
  duration_hours: number;
  duration_minutes?: number;
  travel_minutes?: number;
  search_url: string;
  travel_hours?: number;
};
export type ExpandedPlan = {
  version: 2;
  booking_source?: string;
  trip_id: string;
  currency: string;
  data_source: string;
  legs: {
    origin: string;
    destination: string;
    mode: string;
    departure_date: string;
    arrival_date: string;
    estimated_hours: number;
    estimated_cost: string;
    search_url: string;
    restrictions: FlightPreferences | null;
    alternatives_url?: string;
    selection_status?: string;
    selected_flight?: {
      airlines: string[];
      flight_numbers: string[];
      departure_airport: string;
      arrival_airport: string;
      departure_time: string;
      arrival_time: string;
      stops: number;
      price: string;
      google_flights_url: string | null;
      checked_at: string;
    };
  }[];
  stays: {
    location: string;
    area: string;
    check_in: string;
    check_out: string;
    rooms: number;
    type: string;
    estimated_cost: string;
    search_url: string;
    criteria: string;
    alternatives_url?: string;
    rental_alternatives_url?: string;
    selection_status?: string;
    selected_stay?: {
      name: string;
      rating: number;
      reviews: number;
      location_rating?: number;
      quoted_total: string;
      booking_url: string | null;
      capacity_note: string;
      checked_at: string;
    };
  }[];
  rental_car: {
    searches: { location: string; search_url: string }[];
    estimated_cost: string;
    search_url: string;
    notes: string;
  } | null;
  days: {
    date: string;
    location: string;
    area?: string;
    kind: string;
    title?: string;
    travel_minutes?: number;
    estimated_minutes?: number;
    needs_personalization?: boolean;
    activities: Activity[];
    rain_alternative: { name: string; search_url: string } | null;
  }[];
  destination_estimates: {
    location: string;
    lodging: string;
    food: string;
    activities: string;
    subtotal: string;
  }[];
  suggestion_source: string;
  budget: Record<string, string | null | undefined>;
  assumptions: string[];
  notes: string;
  accessibility: string;
  narrative?: {
    title: string;
    summary: string;
    days: { date: string; description: string; travel_tip: string }[];
  };
};

function Search({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <a
      className="booking-link"
      href={href}
      target="_blank"
      rel="noopener noreferrer"
    >
      {children}
      <NorthEastRounded sx={{ fontSize: 14 }} />
    </a>
  );
}
function visitLength(minutes: number) {
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return hours
    ? `${hours}h${remainder ? ` ${remainder} min` : ""}`
    : `${minutes} min`;
}
const usd = (value: string | null | undefined) =>
  value == null
    ? "—"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 2,
      }).format(Number(value));
export default function ExpandedItinerary({ plan }: { plan: ExpandedPlan }) {
  return (
    <section className="itinerary-stack" aria-label="Your itinerary">
      <Paper
        className="itinerary-panel"
        sx={{ background: "linear-gradient(135deg, #e7efe2, #f6f7ef)" }}
      >
        <span className="section-eyebrow">YOUR ADVENTURE, TAKING SHAPE</span>
        <Typography
          component="h2"
          variant="h4"
          sx={{ fontWeight: 600, mt: 1.5, mb: 2 }}
        >
          {plan.narrative?.title ?? "Room to explore."}
        </Typography>
        {plan.narrative?.summary && (
          <Typography color="text.secondary">
            {plan.narrative.summary}
          </Typography>
        )}
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          A starting point for your trip, with estimated costs and ideas to
          explore. Confirm prices, availability, reviews, and accessibility
          before booking.
        </Typography>
        {plan.suggestion_source === "offline_templates" && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: "block", mt: 1 }}
          >
            Neighborhood suggestions are general starting points, rather than
            verified local recommendations.
          </Typography>
        )}
      </Paper>
      <Paper component="section" className="itinerary-panel">
        <Typography component="h3" className="itinerary-section-title">
          The big picture · estimated costs
        </Typography>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            mb: 3,
            flexWrap: "wrap",
            gap: 1,
          }}
        >
          <Typography variant="h3" sx={{ fontWeight: 550 }}>
            {usd(plan.budget.total)}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Estimated total · USD
          </Typography>
        </Box>
        <dl className="itinerary-budget">
          {[
            "transport",
            "lodging",
            "food",
            "activities",
            "car",
            "contingency",
          ].map((key) => (
            <div key={key}>
              <dt>{key === "car" ? "Car rental" : key}</dt>
              <dd>{usd(plan.budget[key])}</dd>
            </div>
          ))}
        </dl>
        <Divider sx={{ my: 2.5 }} />
        <Stack spacing={1}>
          {plan.budget.per_person_total && (
            <Typography variant="body2" color="text.secondary">
              About {usd(plan.budget.per_person_total)} per person if shared
              evenly. Individual spending can vary.
            </Typography>
          )}
          {plan.budget.target != null && (
            <Typography variant="body2">
              Your target:{" "}
              {usd(plan.budget.entered_amount ?? plan.budget.target)}{" "}
              {plan.budget.basis === "per_person"
                ? "per person"
                : "for the group"}
            </Typography>
          )}
          {plan.budget.limit != null && (
            <Typography variant="body2">
              Spending ceiling: {usd(plan.budget.limit)} for the group
            </Typography>
          )}
          {Number(plan.budget.above_target) > 0 && (
            <Alert severity="info">
              This estimate is{" "}
              {plan.budget.basis === "per_person"
                ? `${usd(plan.budget.per_person_above_target)} per person`
                : `${usd(plan.budget.above_target)} for the group`}{" "}
              above your target.
              {plan.budget.limit != null
                ? " It is within your maximum."
                : " Choose a lower spending style or adjust your trip if you’d like to spend less."}
            </Alert>
          )}
          {plan.budget.target == null && (
            <Typography variant="body2" color="text.secondary">
              Planned for your{" "}
              {
                (
                  {
                    budget: "budget-conscious",
                    value: "good-value",
                    upscale: "upscale",
                  } as Record<string, string>
                )[plan.budget.spending_style ?? "value"]
              }{" "}
              style, without a spending target.
            </Typography>
          )}
        </Stack>
        <Accordion
          disableGutters
          sx={{ mt: 2, "&::before": { display: "none" } }}
        >
          <AccordionSummary expandIcon={<ExpandMoreRounded />}>
            By destination
          </AccordionSummary>
          <AccordionDetails>
            <Stack spacing={2}>
              {plan.destination_estimates.map((item, i) => (
                <Box key={i}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {item.location} · {usd(item.subtotal)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Stays {usd(item.lodging)} · Food {usd(item.food)} ·
                    Activities {usd(item.activities)}
                  </Typography>
                </Box>
              ))}
              <Typography variant="caption" color="text.secondary">
                Transport, transit-day meals, rental cars and contingency are
                included in the overall total.
              </Typography>
            </Stack>
          </AccordionDetails>
        </Accordion>
      </Paper>
      {plan.legs.length > 0 && (
        <section>
          <Typography component="h3" className="itinerary-section-title">
            Getting from here to there.
          </Typography>
          <Stack spacing={2}>
            {plan.legs.map((leg, i) => (
              <Paper component="article" className="itinerary-panel" key={i}>
                <Stack
                  direction="row"
                  spacing={1.2}
                  sx={{ alignItems: "center", mb: 1.5 }}
                >
                  <FlightTakeoffRounded color="primary" />
                  <Typography
                    component="h4"
                    variant="subtitle1"
                    sx={{ fontWeight: 600 }}
                  >
                    {leg.origin} → {leg.destination}
                  </Typography>
                </Stack>
                <Typography
                  variant="body2"
                  sx={{ textTransform: "capitalize" }}
                >
                  {leg.mode} · {dayjs(leg.departure_date).format("MMM D")}
                  {leg.arrival_date !== leg.departure_date &&
                    ` – ${dayjs(leg.arrival_date).format("MMM D")}`}
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ my: 1 }}
                >
                  About {leg.estimated_hours} hours · {usd(leg.estimated_cost)}{" "}
                  estimated for the group
                </Typography>
                {leg.restrictions && (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: "block", mb: 2 }}
                  >
                    Confirm in search: up to {leg.restrictions.max_stops}{" "}
                    stop(s)
                    {leg.restrictions.earliest_departure &&
                      `; depart after ${leg.restrictions.earliest_departure}`}
                    {leg.restrictions.latest_arrival &&
                      `; arrive before ${leg.restrictions.latest_arrival}`}
                    ;{" "}
                    {leg.restrictions.allow_overnight
                      ? "overnight allowed"
                      : "no overnight flights"}
                    . Times are local to each airport.
                  </Typography>
                )}
                {leg.selected_flight && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                      {leg.selected_flight.airlines.join(" / ")} ·{" "}
                      {leg.selected_flight.flight_numbers.join(" / ")}
                    </Typography>
                    <Typography variant="body2">
                      {leg.selected_flight.departure_airport}{" "}
                      {dayjs(leg.selected_flight.departure_time).format(
                        "MMM D, HH:mm",
                      )}{" "}
                      → {leg.selected_flight.arrival_airport}{" "}
                      {dayjs(leg.selected_flight.arrival_time).format(
                        "MMM D, HH:mm",
                      )}
                    </Typography>
                    <Typography variant="body2" sx={{ my: 1 }}>
                      Provider quote: {usd(leg.selected_flight.price)} ·{" "}
                      {leg.selected_flight.stops === 0
                        ? "Nonstop"
                        : `${leg.selected_flight.stops} stop(s)`}
                    </Typography>
                    {leg.selected_flight.google_flights_url && (
                      <Search href={leg.selected_flight.google_flights_url}>
                        View selected flight on Google Flights
                      </Search>
                    )}
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: "block", mt: 1 }}
                    >
                      Checked{" "}
                      {dayjs(leg.selected_flight.checked_at).format(
                        "MMM D, HH:mm",
                      )}
                      . Confirm final traveler fares, luggage and availability.
                    </Typography>
                  </Box>
                )}
                {leg.mode === "flight" && !leg.selected_flight && (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: "block", mb: 1 }}
                  >
                    No matching live flight quote was retrieved. Compare options
                    for these dates below.
                  </Typography>
                )}
                <Search href={leg.alternatives_url ?? leg.search_url}>
                  {leg.mode === "flight"
                    ? `Other flights on ${dayjs(leg.departure_date).format("MMM D")} · ${leg.restrictions?.max_stops === 0 ? "nonstop" : `up to ${leg.restrictions?.max_stops ?? 1} stop(s)`}`
                    : "Compare transport options"}
                </Search>
              </Paper>
            ))}
          </Stack>
        </section>
      )}
      <section>
        <Typography component="h3" className="itinerary-section-title">
          Somewhere to call home, for a while.
        </Typography>
        <Stack spacing={2}>
          {plan.stays.map((stay, i) => (
            <Paper component="article" className="itinerary-panel" key={i}>
              <Stack
                direction="row"
                spacing={1.2}
                sx={{ alignItems: "center", mb: 1.5 }}
              >
                <HotelRounded color="primary" />
                <Typography
                  component="h4"
                  variant="subtitle1"
                  sx={{ fontWeight: 600 }}
                >
                  {stay.location}
                </Typography>
              </Stack>
              <Typography variant="body2">
                {stay.area} · {dayjs(stay.check_in).format("MMM D")} –{" "}
                {dayjs(stay.check_out).format("MMM D")} · {stay.rooms} room(s)
              </Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                {usd(stay.estimated_cost)} estimated stay total
              </Typography>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ display: "block", my: 1.5 }}
              >
                {stay.criteria}
              </Typography>
              {stay.selected_stay && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                    {stay.selected_stay.name}
                  </Typography>
                  <Typography variant="body2">
                    {stay.selected_stay.rating}/5 from{" "}
                    {stay.selected_stay.reviews} reviews
                  </Typography>
                  <Typography variant="body2" sx={{ my: 1 }}>
                    Quoted stay rate: {usd(stay.selected_stay.quoted_total)}
                  </Typography>
                  {stay.selected_stay.booking_url && (
                    <Search href={stay.selected_stay.booking_url}>
                      View recommended stay
                    </Search>
                  )}
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: "block", mt: 1 }}
                  >
                    {stay.selected_stay.capacity_note} Checked{" "}
                    {dayjs(stay.selected_stay.checked_at).format(
                      "MMM D, HH:mm",
                    )}
                    .
                  </Typography>
                </Box>
              )}
              {!stay.selected_stay && (
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ display: "block", mb: 1 }}
                >
                  No live property recommendation was retrieved. Search your
                  dates and guest requirements below.
                </Typography>
              )}
              <Stack spacing={1}>
                <Search href={stay.alternatives_url ?? stay.search_url}>
                  Other hotels for your dates
                </Search>
                {stay.rental_alternatives_url && (
                  <Search href={stay.rental_alternatives_url}>
                    Vacation rental alternatives on Airbnb
                  </Search>
                )}
              </Stack>
            </Paper>
          ))}
        </Stack>
      </section>
      {plan.rental_car && (
        <Paper component="section" className="itinerary-panel">
          <Typography component="h3" className="itinerary-section-title">
            Freedom on four wheels.
          </Typography>
          <Typography variant="body2">
            Group allowance: {usd(plan.rental_car.estimated_cost)}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ my: 1.5 }}>
            {plan.rental_car.notes}
          </Typography>
          <Stack spacing={1}>
            {plan.rental_car.searches.map((search, i) => (
              <Search key={i} href={search.search_url}>
                Find a car in {search.location}
              </Search>
            ))}
          </Stack>
        </Paper>
      )}
      <section>
        <Typography component="h3" className="itinerary-section-title">
          Your days, with room to wander.
        </Typography>
        <Stack spacing={2.5}>
          {plan.days.map((day) => (
            <Paper
              component="article"
              key={day.date}
              className="itinerary-panel"
            >
              <div className="day-heading">
                <div className="day-number">
                  <span>{dayjs(day.date).format("MMM")}</span>
                  {dayjs(day.date).format("D")}
                </div>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                    {day.title ?? day.location}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {dayjs(day.date).format("dddd")}
                    {day.area && ` · ${day.area}`}
                  </Typography>
                </Box>
                <Chip
                  size="small"
                  variant="outlined"
                  label={
                    day.kind === "arrival"
                      ? "Easy arrival"
                      : day.kind === "full"
                        ? "Explore"
                        : "Travel day"
                  }
                  sx={{ fontSize: 10 }}
                />
              </div>
              {!!day.travel_minutes && (
                <Typography variant="body2" color="text.secondary">
                  Allow about {visitLength(day.travel_minutes)} round-trip
                  travel for this excursion.
                </Typography>
              )}
              {day.activities.length === 0 && (
                <Typography variant="body2" color="text.secondary">
                  A little breathing room for travel, check-out, and
                  connections.
                </Typography>
              )}
              {day.activities.map((a) => (
                <div className="activity-row" key={a.id}>
                  <Search href={a.search_url}>{a.name}</Search>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 0.7 }}
                  >
                    About{" "}
                    {visitLength(
                      a.duration_minutes ?? Math.round(a.duration_hours * 60),
                    )}{" "}
                    · {usd(a.price_per_person)} per person
                    {a.travel_hours !== undefined &&
                      ` · includes about ${a.travel_hours} hours round-trip travel`}
                  </Typography>
                </div>
              ))}
              {plan.narrative?.days.find((d) => d.date === day.date)
                ?.description && (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 2 }}
                >
                  {
                    plan.narrative.days.find((d) => d.date === day.date)
                      ?.description
                  }
                </Typography>
              )}
              {day.rain_alternative && (
                <Accordion
                  disableGutters
                  sx={{
                    mt: 1.5,
                    "&::before": { display: "none" },
                    bgcolor: "#f6f8f1",
                    borderRadius: "10px !important",
                  }}
                >
                  <AccordionSummary expandIcon={<ExpandMoreRounded />}>
                    <Stack
                      direction="row"
                      spacing={1}
                      sx={{ alignItems: "center" }}
                    >
                      <UmbrellaRounded sx={{ fontSize: 17 }} />
                      <Typography variant="body2">
                        If the weather has other plans…
                      </Typography>
                    </Stack>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Search href={day.rain_alternative.search_url}>
                      {day.rain_alternative.name}
                    </Search>
                    <Typography
                      variant="caption"
                      sx={{ mt: 1, display: "block" }}
                      color="text.secondary"
                    >
                      A swap, not an extra activity. Admission costs aren’t
                      included in the estimate.
                    </Typography>
                  </AccordionDetails>
                </Accordion>
              )}
            </Paper>
          ))}
        </Stack>
      </section>
      <Accordion
        variant="outlined"
        sx={{
          borderRadius: "14px !important",
          "&::before": { display: "none" },
        }}
      >
        <AccordionSummary expandIcon={<ExpandMoreRounded />}>
          The details behind your plan
        </AccordionSummary>
        <AccordionDetails>
          <Stack spacing={1.5}>
            {plan.assumptions.map((a, i) => (
              <Typography variant="body2" color="text.secondary" key={i}>
                {a}
              </Typography>
            ))}
            {plan.notes && (
              <Typography variant="body2">Your notes: {plan.notes}</Typography>
            )}
            {plan.accessibility && (
              <Typography variant="body2">
                Accessibility to confirm: {plan.accessibility}
              </Typography>
            )}
          </Stack>
        </AccordionDetails>
      </Accordion>
    </section>
  );
}
