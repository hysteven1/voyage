"use client";

import { FormEvent, ReactNode, useRef, useState } from "react";
import dayjs from "dayjs";
import Link from "next/link";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Divider,
  FormControlLabel,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from "@mui/material";
import ExploreRounded from "@mui/icons-material/ExploreRounded";
import FlightTakeoffRounded from "@mui/icons-material/FlightTakeoffRounded";
import DirectionsCarRounded from "@mui/icons-material/DirectionsCarRounded";
import LocationOnRounded from "@mui/icons-material/LocationOnRounded";
import AddRounded from "@mui/icons-material/AddRounded";
import ArrowForwardRounded from "@mui/icons-material/ArrowForwardRounded";
import ArrowBackRounded from "@mui/icons-material/ArrowBackRounded";
import DeleteOutlineRounded from "@mui/icons-material/DeleteOutlineRounded";
import ExpandMoreRounded from "@mui/icons-material/ExpandMoreRounded";
import NorthRounded from "@mui/icons-material/NorthRounded";
import SouthRounded from "@mui/icons-material/SouthRounded";
import CheckRounded from "@mui/icons-material/CheckRounded";
import HotelRounded from "@mui/icons-material/HotelRounded";
import SpaRounded from "@mui/icons-material/SpaRounded";
import ParkRounded from "@mui/icons-material/ParkRounded";
import RestaurantRounded from "@mui/icons-material/RestaurantRounded";
import MuseumRounded from "@mui/icons-material/MuseumRounded";
import HikingRounded from "@mui/icons-material/HikingRounded";
import TripItinerary from "@/components/TripItinerary";
import TravelScene from "@/components/TravelScene";
import TravelDates from "@/components/form/TravelDates";
import LocationAutocomplete from "@/components/form/LocationAutocomplete";
import {
  api,
  FlightPreferences,
  flightDefaults,
  newStop,
  Options,
  Stop,
  TripForm,
} from "@/lib/trip";

const interests = [
  { name: "Food", icon: <RestaurantRounded /> },
  { name: "Nature", icon: <ParkRounded /> },
  { name: "Culture", icon: <MuseumRounded /> },
  { name: "Adventure", icon: <HikingRounded /> },
  { name: "Relaxation", icon: <SpaRounded /> },
];
const initial: TripForm = {
  origin: "",
  start_date: "",
  end_date: "",
  travelers: 2,
  budget: 3000,
  preferences: [],
  options: {
    journey: "flying",
    route: [newStop()],
    endpoint: "return",
    end_location: null,
    return_mode: "flight",
    return_travel_days: 0,
    return_flight_preferences: null,
    adults: 2,
    child_ages: [],
    rooms: 1,
    accessibility: "",
    budget_mode: "strict",
    maximum_budget: null,
    pace: "balanced",
    lodging: "either",
    rental_car: false,
    notes: "",
  },
};
type Proposal = {
  options: Options;
  assumptions: string[];
  source: string;
  conflicts: string[];
};

export default function Home() {
  const [form, setForm] = useState(initial);
  const [step, setStep] = useState(0);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [tripId, setTripId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);
  const o = form.options;
  const field = <K extends keyof TripForm>(key: K, value: TripForm[K]) =>
    setForm((old) => ({ ...old, [key]: value }));
  const option = <K extends keyof Options>(key: K, value: Options[K]) =>
    field("options", { ...o, [key]: value });
  const updateStop = (index: number, change: Partial<Stop>) =>
    option(
      "route",
      o.route.map((s, i) => (i === index ? { ...s, ...change } : s)),
    );
  const nights =
    form.start_date && form.end_date
      ? dayjs(form.end_date).diff(dayjs(form.start_date), "day")
      : 0;
  const allocated =
    o.route.reduce((sum, s) => sum + (s.nights ?? 0) + s.travel_days, 0) +
    (o.endpoint === "one_way" ? 0 : o.return_travel_days);
  const people = o.adults + o.child_ages.length;

  function navigate(next: number) {
    setStep(next);
    setError("");
    requestAnimationFrame(() => {
      heading.current?.focus();
      document
        .getElementById("planner")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (step === 0) {
      const origin = form.origin?.trim() ?? "";
      if (origin.length === 1 || (!origin && o.journey !== "already_there")) {
        setError("Enter your starting city or choose a location suggestion.");
        return;
      }
      if (!form.start_date || !form.end_date || nights < 1 || nights > 90) {
        setError(
          "Choose departure and return dates, between 1 and 90 nights apart.",
        );
        return;
      }
      if (o.route.some((s) => s.location.trim().length < 2)) {
        setError("Add a city or country for each destination.");
        return;
      }
      if (
        new Set(o.route.map((stop) => stop.location.trim().toLowerCase()))
          .size !== o.route.length
      ) {
        setError(
          "List each destination once. You can adjust the nights at each stop later.",
        );
        return;
      }
      navigate(1);
      return;
    }
    setLoading(true);
    const options: Options = {
      ...o,
      endpoint: o.journey === "already_there" ? "one_way" : "return",
      end_location: null,
    };
    const payload = {
      ...form,
      options,
      origin: form.origin?.trim() || null,
      travelers: people,
    };
    try {
      if (step === 1) {
        const result = await api<Proposal>(
          "/api/v1/trips/route-proposal",
          payload,
        );
        field("options", result.options);
        setProposal(result);
        setConfirmed(false);
        navigate(2);
      } else {
        const result = await api<{ id: string }>("/api/v1/trips", payload);
        setTripId(result.id);
        requestAnimationFrame(() =>
          document
            .getElementById("planner")
            ?.scrollIntoView({ behavior: "smooth" }),
        );
      }
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Unable to plan trip. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  function updateGroup(adults: number, child_ages: number[]) {
    const count = adults + child_ages.length;
    field("options", {
      ...o,
      adults,
      child_ages,
      rooms: Math.min(count, Math.max(Math.ceil(count / 4), o.rooms)),
    });
  }

  function moveStop(index: number, direction: number) {
    const route = [...o.route];
    [route[index], route[index + direction]] = [
      route[index + direction],
      route[index],
    ];
    // Transit belongs to the incoming leg; recheck after reordering.
    option("route", route);
    setConfirmed(false);
  }

  return (
    <div className="voyage-site">
      <header className="site-header">
        <Link className="wordmark" href="/" aria-label="Voyage home">
          <span className="brand-icon">
            <ExploreRounded />
          </span>
          voyage<span className="brand-dot">.</span>
        </Link>
        <nav aria-label="Main navigation">
          <a href="#planner">Plan a trip</a>
          <a href="#how-it-works">How it works</a>
        </nav>
        <span className="header-note">
          A little less planning. A lot more living.
        </span>
      </header>
      <main>
        <section className="hero">
          <div className="hero-eyebrow">
            <span /> MADE FOR YOUR KIND OF TRAVEL
          </div>
          <h1>
            The world is calling.
            <br />
            Make it <em>your kind of trip.</em>
          </h1>
          <p>
            Big adventures, slow mornings, and everything in between.
            <br className="desktop-break" /> Tell us what you love. We’ll help
            you find your way.
          </p>
          <div className="hero-tags">
            <span>
              <CheckRounded /> A route that makes sense
            </span>
            <span>
              <CheckRounded /> A budget that works for you
            </span>
            <span>
              <CheckRounded /> Room to wander
            </span>
          </div>
        </section>
        <div className="planner-layout" id="planner">
          <div className="planner-main">
            {!tripId ? (
              <Paper
                component="form"
                onSubmit={submit}
                className="planner-card"
                aria-busy={loading}
              >
                <Stepper
                  activeStep={step}
                  alternativeLabel
                  className="planner-stepper"
                >
                  {["The essentials", "Your travel style", "Make it yours"].map(
                    (label) => (
                      <Step key={label}>
                        <StepLabel>{label}</StepLabel>
                      </Step>
                    ),
                  )}
                </Stepper>
                <Divider sx={{ my: 3.5 }} />
                <div className="form-heading">
                  <span className="section-eyebrow">STEP 0{step + 1}</span>
                  <Typography
                    component="h2"
                    tabIndex={-1}
                    ref={heading}
                    variant="h4"
                    sx={{
                      fontWeight: 600,
                      letterSpacing: "-.04em",
                      outline: "none",
                    }}
                  >
                    {
                      [
                        "Where will curiosity take you?",
                        "What does your perfect trip feel like?",
                        "A little fine-tuning. Then, adventure.",
                      ][step]
                    }
                  </Typography>
                  <Typography color="text.secondary" sx={{ mt: 1 }}>
                    {
                      [
                        "Start with the big picture. We’ll help with the little details.",
                        "The best itineraries start with what matters to you.",
                        "Your route is a starting point. Adjust it until it feels right.",
                      ][step]
                    }
                  </Typography>
                </div>
                <fieldset disabled={loading} className="form-fields">
                  {step === 0 && (
                    <>
                      <FormSection title="How are you getting there?">
                        <div className="choice-grid three">
                          <Choice
                            selected={o.journey === "flying"}
                            title="Flying"
                            subtitle="Find a new horizon"
                            icon={<FlightTakeoffRounded />}
                            onClick={() => option("journey", "flying")}
                          />
                          <Choice
                            selected={o.journey === "driving"}
                            title="Road trip"
                            subtitle="Take the scenic route"
                            icon={<DirectionsCarRounded />}
                            onClick={() => option("journey", "driving")}
                          />
                          <Choice
                            selected={o.journey === "already_there"}
                            title="Already there"
                            subtitle="Explore from here"
                            icon={<LocationOnRounded />}
                            onClick={() => option("journey", "already_there")}
                          />
                        </div>
                      </FormSection>
                      <FormSection title="Let’s put a pin in the map.">
                        <LocationAutocomplete
                          label={
                            o.journey === "already_there"
                              ? "From (optional)"
                              : "From"
                          }
                          value={form.origin ?? ""}
                          required={o.journey !== "already_there"}
                          onChange={(value) => field("origin", value)}
                          placeholder="Start typing a city, e.g. New York"
                          citiesOnly
                        />
                        <div className="destinations-list">
                          {o.route.map((s, i) => (
                            <div className="destination-row" key={i}>
                              <span className="stop-number">
                                {String(i + 1).padStart(2, "0")}
                              </span>
                              <LocationAutocomplete
                                label={
                                  o.route.length > 1
                                    ? `Destination ${i + 1}`
                                    : "Where to?"
                                }
                                value={s.location}
                                required
                                onChange={(value) =>
                                  updateStop(i, { location: value })
                                }
                                placeholder="Try Tokyo, Japan…"
                              />
                              <IconButton
                                aria-label={`Remove destination ${i + 1}`}
                                disabled={o.route.length === 1}
                                onClick={() =>
                                  option(
                                    "route",
                                    o.route.filter((_, n) => n !== i),
                                  )
                                }
                              >
                                <DeleteOutlineRounded />
                              </IconButton>
                            </div>
                          ))}
                        </div>
                        <Button
                          startIcon={<AddRounded />}
                          disabled={o.route.length >= 10}
                          onClick={() =>
                            option("route", [...o.route, newStop()])
                          }
                        >
                          Add another stop
                        </Button>
                      </FormSection>
                      <FormSection title="Clear your calendar.">
                        <TravelDates
                          start={form.start_date}
                          end={form.end_date}
                          onChange={(start, end) =>
                            setForm((old) => ({
                              ...old,
                              start_date: start,
                              end_date: end,
                            }))
                          }
                        />
                        {nights > 0 && (
                          <Chip
                            size="small"
                            label={`${nights} nights of possibility`}
                            sx={{
                              mt: 1.5,
                              bgcolor: "#edf3e9",
                              alignSelf: "flex-start",
                            }}
                          />
                        )}
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{ mt: 1.5 }}
                        >
                          {o.journey === "already_there"
                            ? "We’ll plan from your first destination, without an outbound or return journey."
                            : "Travel days are included. We’ll plan your return to where you started."}
                        </Typography>
                      </FormSection>
                    </>
                  )}
                  {step === 1 && (
                    <>
                      <FormSection
                        title="Who’s coming along?"
                        subtitle="So there’s a seat, a room, and a little adventure for everyone."
                      >
                        <div className="counter-grid">
                          <Counter
                            label="Adults"
                            detail="18 and over"
                            value={o.adults}
                            min={1}
                            max={20 - o.child_ages.length}
                            onChange={(n) => updateGroup(n, o.child_ages)}
                          />
                          <Counter
                            label="Children"
                            detail="Under 18"
                            value={o.child_ages.length}
                            min={0}
                            max={20 - o.adults}
                            onChange={(n) =>
                              updateGroup(
                                o.adults,
                                Array.from(
                                  { length: n },
                                  (_, i) => o.child_ages[i] ?? 5,
                                ),
                              )
                            }
                          />
                          <Counter
                            label="Rooms"
                            detail="For your group"
                            value={o.rooms}
                            min={Math.ceil(people / 4)}
                            max={people}
                            onChange={(n) => option("rooms", n)}
                          />
                        </div>
                        {o.child_ages.length > 0 && (
                          <div className="field-grid three">
                            {o.child_ages.map((age, i) => (
                              <TextField
                                select
                                label={`Child ${i + 1} age`}
                                key={i}
                                value={age}
                                onChange={(e) =>
                                  option(
                                    "child_ages",
                                    o.child_ages.map((a, n) =>
                                      n === i ? +e.target.value : a,
                                    ),
                                  )
                                }
                              >
                                {Array.from({ length: 18 }, (_, n) => (
                                  <MenuItem value={n} key={n}>
                                    {n === 0 ? "Under 1" : n}
                                  </MenuItem>
                                ))}
                              </TextField>
                            ))}
                          </div>
                        )}
                      </FormSection>
                      <FormSection
                        title="A good trip. A comfortable budget."
                        subtitle="One total for your whole group: transport, stays, food, activities, and a little cushion."
                      >
                        <TextField
                          required
                          label="Trip budget · USD"
                          type="number"
                          value={form.budget}
                          slotProps={{ htmlInput: { min: 1, step: "0.01" } }}
                          onChange={(e) => field("budget", +e.target.value)}
                        />
                        <div className="choice-grid two">
                          <Choice
                            selected={o.budget_mode === "strict"}
                            title="Keep it within budget"
                            subtitle="This is my spending ceiling"
                            onClick={() => option("budget_mode", "strict")}
                          />
                          <Choice
                            selected={o.budget_mode === "flexible"}
                            title="A little room to stretch"
                            subtitle="Worth it for the right experience"
                            onClick={() => option("budget_mode", "flexible")}
                          />
                        </div>
                        {o.budget_mode === "flexible" && (
                          <TextField
                            label="Most you’d be comfortable spending · USD"
                            type="number"
                            required
                            value={o.maximum_budget ?? ""}
                            slotProps={{
                              htmlInput: { min: form.budget, step: "0.01" },
                            }}
                            onChange={(e) =>
                              option("maximum_budget", +e.target.value)
                            }
                          />
                        )}
                      </FormSection>
                      <FormSection title="Find your rhythm.">
                        <div className="choice-grid three">
                          {[
                            {
                              value: "relaxed",
                              title: "Slow & easy",
                              subtitle: "Space to soak it in",
                            },
                            {
                              value: "balanced",
                              title: "A little of everything",
                              subtitle: "Explore, then exhale",
                            },
                            {
                              value: "busy",
                              title: "See it all",
                              subtitle: "Make every day count",
                            },
                          ].map((p) => (
                            <Choice
                              key={p.value}
                              selected={o.pace === p.value}
                              title={p.title}
                              subtitle={p.subtitle}
                              onClick={() =>
                                option("pace", p.value as Options["pace"])
                              }
                            />
                          ))}
                        </div>
                      </FormSection>
                      <FormSection
                        title="What draws you in?"
                        subtitle="Pick as many as you like."
                      >
                        <Stack
                          direction="row"
                          sx={{ gap: 1.2, flexWrap: "wrap" }}
                        >
                          {interests.map((p) => (
                            <Chip
                              key={p.name}
                              clickable
                              icon={p.icon}
                              label={p.name}
                              onClick={() =>
                                field(
                                  "preferences",
                                  form.preferences.includes(p.name)
                                    ? form.preferences.filter(
                                        (v) => v !== p.name,
                                      )
                                    : [...form.preferences, p.name],
                                )
                              }
                              color={
                                form.preferences.includes(p.name)
                                  ? "primary"
                                  : "default"
                              }
                              variant={
                                form.preferences.includes(p.name)
                                  ? "filled"
                                  : "outlined"
                              }
                              aria-pressed={form.preferences.includes(p.name)}
                              sx={{ height: 42, px: 1 }}
                            />
                          ))}
                        </Stack>
                      </FormSection>
                      <FormSection title="Somewhere to land.">
                        <TextField
                          select
                          label="Where do you like to stay?"
                          value={o.lodging}
                          onChange={(e) =>
                            option(
                              "lodging",
                              e.target.value as Options["lodging"],
                            )
                          }
                        >
                          <MenuItem value="either">
                            Open to hotels & apartments
                          </MenuItem>
                          <MenuItem value="hotel">Hotels</MenuItem>
                          <MenuItem value="apartment">
                            Apartments & Airbnbs
                          </MenuItem>
                        </TextField>
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={o.rental_car}
                              onChange={(e) =>
                                option("rental_car", e.target.checked)
                              }
                            />
                          }
                          label="I’m interested in renting a car"
                        />
                      </FormSection>
                      <FormSection title="The little details matter.">
                        <TextField
                          label="Accessibility needs (optional)"
                          multiline
                          minRows={2}
                          value={o.accessibility}
                          placeholder="Step-free access, shorter walks, or anything else to keep in mind"
                          slotProps={{ htmlInput: { maxLength: 1000 } }}
                          onChange={(e) =>
                            option("accessibility", e.target.value)
                          }
                        />
                        <TextField
                          label="Anything else on your mind? (optional)"
                          multiline
                          minRows={3}
                          value={o.notes}
                          placeholder="A restaurant you’ve dreamed of, a special occasion, a travel constraint…"
                          slotProps={{ htmlInput: { maxLength: 3000 } }}
                          onChange={(e) => option("notes", e.target.value)}
                        />
                      </FormSection>
                    </>
                  )}
                  {step === 2 && (
                    <>
                      <Alert
                        severity={allocated === nights ? "success" : "warning"}
                      >
                        {allocated === nights
                          ? `All ${nights} nights accounted for. Looking good.`
                          : `${allocated} of ${nights} nights allocated. Adjust stays or transit nights to match your dates.`}
                      </Alert>
                      <Typography variant="body2" color="text.secondary">
                        We keep arrival days light. Move stops, adjust your
                        nights, and review the connections between them.
                      </Typography>
                      {o.route.map((s, i) => (
                        <Paper
                          variant="outlined"
                          className="route-card"
                          key={i}
                        >
                          <div className="route-card-heading">
                            <span className="stop-number">
                              {String(i + 1).padStart(2, "0")}
                            </span>
                            <Typography
                              component="h3"
                              variant="h6"
                              sx={{ flex: 1 }}
                            >
                              Your {i + 1 === 1 ? "first" : "next"} stop
                            </Typography>
                            <IconButton
                              aria-label={`Move stop ${i + 1} earlier`}
                              disabled={i === 0}
                              onClick={() => moveStop(i, -1)}
                            >
                              <NorthRounded fontSize="small" />
                            </IconButton>
                            <IconButton
                              aria-label={`Move stop ${i + 1} later`}
                              disabled={i === o.route.length - 1}
                              onClick={() => moveStop(i, 1)}
                            >
                              <SouthRounded fontSize="small" />
                            </IconButton>
                          </div>
                          <LocationAutocomplete
                            label="Destination"
                            value={s.location}
                            required
                            onChange={(v) => updateStop(i, { location: v })}
                          />
                          <Counter
                            label="Nights here"
                            detail="Time to explore"
                            value={s.nights ?? 1}
                            min={1}
                            max={90}
                            onChange={(n) => updateStop(i, { nights: n })}
                          />
                          {!(i === 0 && o.journey === "already_there") && (
                            <Accordion
                              disableGutters
                              elevation={0}
                              sx={{ "&::before": { display: "none" } }}
                            >
                              <AccordionSummary
                                expandIcon={<ExpandMoreRounded />}
                              >
                                Getting here ·{" "}
                                {s.mode === "flight"
                                  ? "Flight"
                                  : s.mode === "drive"
                                    ? "Drive"
                                    : "Train"}
                              </AccordionSummary>
                              <AccordionDetails>
                                <TravelLeg
                                  mode={s.mode}
                                  transit={s.travel_days}
                                  driving={o.journey === "driving"}
                                  onMode={(v) => updateStop(i, { mode: v })}
                                  onTransit={(n) =>
                                    updateStop(i, { travel_days: n })
                                  }
                                />
                                {s.mode === "flight" && (
                                  <FlightFields
                                    value={
                                      s.flight_preferences ?? flightDefaults
                                    }
                                    onChange={(v) =>
                                      updateStop(i, { flight_preferences: v })
                                    }
                                  />
                                )}
                              </AccordionDetails>
                            </Accordion>
                          )}
                        </Paper>
                      ))}
                      {o.endpoint !== "one_way" && (
                        <Accordion
                          variant="outlined"
                          disableGutters
                          sx={{
                            borderRadius: "14px !important",
                            "&::before": { display: "none" },
                          }}
                        >
                          <AccordionSummary expandIcon={<ExpandMoreRounded />}>
                            <Stack
                              direction="row"
                              spacing={1}
                              sx={{ alignItems: "center" }}
                            >
                              <FlightTakeoffRounded fontSize="small" />
                              <span>Back to {form.origin}</span>
                            </Stack>
                          </AccordionSummary>
                          <AccordionDetails>
                            <TravelLeg
                              mode={o.return_mode}
                              transit={o.return_travel_days}
                              driving={o.journey === "driving"}
                              onMode={(v) => option("return_mode", v)}
                              onTransit={(n) => option("return_travel_days", n)}
                            />
                            {o.return_mode === "flight" && (
                              <FlightFields
                                value={
                                  o.return_flight_preferences ?? flightDefaults
                                }
                                onChange={(v) =>
                                  option("return_flight_preferences", v)
                                }
                              />
                            )}
                          </AccordionDetails>
                        </Accordion>
                      )}
                      <Accordion
                        disableGutters
                        sx={{
                          bgcolor: "#f7f8f3",
                          "&::before": { display: "none" },
                          borderRadius: "12px !important",
                        }}
                      >
                        <AccordionSummary expandIcon={<ExpandMoreRounded />}>
                          A few things to double-check
                        </AccordionSummary>
                        <AccordionDetails>
                          <Stack spacing={1.5}>
                            {proposal?.assumptions.map((a, i) => (
                              <Typography
                                variant="body2"
                                color="text.secondary"
                                key={i}
                              >
                                {a}
                              </Typography>
                            ))}
                            {o.notes && (
                              <Typography variant="body2">
                                Your notes: {o.notes}
                              </Typography>
                            )}
                            {o.accessibility && (
                              <Typography variant="body2">
                                Accessibility: {o.accessibility}
                              </Typography>
                            )}
                          </Stack>
                        </AccordionDetails>
                      </Accordion>
                      {proposal?.conflicts.map((conflict, i) => (
                        <Alert severity="warning" key={i}>
                          {conflict}. Go back to update your preferences, then
                          suggest the route again.
                        </Alert>
                      ))}
                      <FormControlLabel
                        sx={{ alignItems: "flex-start", m: 0 }}
                        control={
                          <Checkbox
                            required
                            checked={confirmed}
                            onChange={(e) => setConfirmed(e.target.checked)}
                            sx={{ pt: 0.3 }}
                          />
                        }
                        label={
                          <Typography variant="body2">
                            This route feels right. I’ll confirm travel times,
                            prices, and availability before booking.
                          </Typography>
                        }
                      />
                    </>
                  )}
                </fieldset>
                {error && (
                  <Alert severity="error" sx={{ mt: 3 }} role="alert">
                    {error}
                  </Alert>
                )}
                <div className="form-footer">
                  {step > 0 ? (
                    <Button
                      startIcon={<ArrowBackRounded />}
                      disabled={loading}
                      onClick={() => navigate(step - 1)}
                    >
                      Back
                    </Button>
                  ) : (
                    <Typography variant="caption" color="text.secondary">
                      Every great trip starts somewhere.
                    </Typography>
                  )}
                  <Button
                    variant="contained"
                    type="submit"
                    size="large"
                    endIcon={
                      loading ? (
                        <CircularProgress size={18} color="inherit" />
                      ) : (
                        <ArrowForwardRounded />
                      )
                    }
                    disabled={
                      loading ||
                      (step === 2 &&
                        (allocated !== nights ||
                          !confirmed ||
                          !!proposal?.conflicts.length))
                    }
                  >
                    {loading
                      ? "Finding your way…"
                      : [
                          "Make it personal",
                          "Find my route",
                          "Let’s plan this trip",
                        ][step]}
                  </Button>
                </div>
              </Paper>
            ) : (
              <>
                <Paper className="saved-card">
                  <Chip
                    icon={<CheckRounded />}
                    color="primary"
                    label="Your route is ready"
                  />
                  <Typography variant="h4" sx={{ mt: 2, fontWeight: 600 }}>
                    The good part starts here.
                  </Typography>
                  <Typography color="text.secondary" sx={{ my: 2 }}>
                    Generate your day-by-day itinerary, with ideas for what to
                    do and where to stay.
                  </Typography>
                  <Button
                    variant="outlined"
                    onClick={() => {
                      setTripId(null);
                      setProposal(null);
                      navigate(0);
                    }}
                  >
                    Change details & start a new plan
                  </Button>
                </Paper>
                <TripItinerary key={tripId} tripId={tripId} />
              </>
            )}
          </div>
          <aside className="trip-sidebar">
            <TravelScene />
            <div className="sidebar-content">
              <span className="section-eyebrow">YOUR NEXT CHAPTER</span>
              <h2>
                A trip that feels
                <br />
                <em>like you.</em>
              </h2>
              <p>The best plans leave room for a little serendipity.</p>
              <Divider sx={{ my: 3 }} />
              <Stack spacing={2.5}>
                <SummaryRow
                  icon={<LocationOnRounded />}
                  label="The places"
                  value={
                    o.route
                      .map((s) => s.location)
                      .filter(Boolean)
                      .join(" → ") || "Somewhere wonderful"
                  }
                />
                <SummaryRow
                  icon={<ExploreRounded />}
                  label="The time"
                  value={
                    form.start_date && form.end_date
                      ? `${dayjs(form.start_date).format("MMM D")} – ${dayjs(form.end_date).format("MMM D")} · ${nights} nights`
                      : "A little time away"
                  }
                />
                <SummaryRow
                  icon={<HotelRounded />}
                  label="The company"
                  value={`${people} traveler${people !== 1 ? "s" : ""} · ${o.rooms} room${o.rooms !== 1 ? "s" : ""}`}
                />
              </Stack>
              <div className="sidebar-budget">
                <span>YOUR GROUP BUDGET</span>
                <strong>
                  {new Intl.NumberFormat("en-US", {
                    style: "currency",
                    currency: "USD",
                    maximumFractionDigits: 0,
                  }).format(form.budget || 0)}
                </strong>
                <span>
                  {o.budget_mode === "strict"
                    ? "We’ll keep your estimate within this."
                    : `Up to $${o.maximum_budget || "…"} for the right experience.`}
                </span>
              </div>
            </div>
            <p className="sidebar-footnote">
              Thoughtful suggestions. Real possibilities.
              <br />
              Always confirm details before booking.
            </p>
          </aside>
        </div>
        <section className="how-it-works" id="how-it-works">
          <div>
            <span className="section-eyebrow">LESS ADMIN. MORE ADVENTURE.</span>
            <h2>
              A good trip starts with
              <br />a plan that feels easy.
            </h2>
          </div>
          <div className="how-step">
            <span>01</span>
            <h3>Tell us your kind of trip.</h3>
            <p>The places, the pace, and the things you love.</p>
          </div>
          <div className="how-step">
            <span>02</span>
            <h3>Find your flow.</h3>
            <p>Review a route that makes room for your priorities.</p>
          </div>
          <div className="how-step">
            <span>03</span>
            <h3>Make it happen.</h3>
            <p>Explore your itinerary and follow booking searches.</p>
          </div>
        </section>
      </main>
      <footer className="site-footer">
        <Link className="wordmark" href="/">
          voyage<span className="brand-dot">.</span>
        </Link>
        <p>Go somewhere that stays with you.</p>
        <span>
          Location data:{" "}
          <a href="https://www.geonames.org/" target="_blank" rel="noreferrer">
            GeoNames
          </a>{" "}
          ·{" "}
          <a
            href="https://creativecommons.org/licenses/by/4.0/"
            target="_blank"
            rel="noreferrer"
          >
            CC BY 4.0
          </a>
        </span>
      </footer>
    </div>
  );
}

function FormSection({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section className="form-section">
      <Typography component="h3" variant="subtitle1" sx={{ fontWeight: 650 }}>
        {title}
      </Typography>
      {subtitle && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: -0.5 }}>
          {subtitle}
        </Typography>
      )}
      {children}
    </section>
  );
}
function Choice({
  selected,
  title,
  subtitle,
  icon,
  onClick,
}: {
  selected: boolean;
  title: string;
  subtitle: string;
  icon?: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={`choice-card ${selected ? "selected" : ""}`}
      aria-pressed={selected}
      onClick={onClick}
    >
      {icon && <span className="choice-icon">{icon}</span>}
      <strong>{title}</strong>
      <span>{subtitle}</span>
      {selected && <CheckRounded className="choice-check" />}
    </button>
  );
}
function Counter({
  label,
  detail,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  detail: string;
  value: number;
  min: number;
  max: number;
  onChange: (n: number) => void;
}) {
  return (
    <div className="counter">
      <div>
        <strong>{label}</strong>
        <span>{detail}</span>
      </div>
      <div className="counter-controls">
        <IconButton
          size="small"
          aria-label={`Decrease ${label.toLowerCase()}`}
          disabled={value <= min}
          onClick={() => onChange(value - 1)}
        >
          <span aria-hidden="true">−</span>
        </IconButton>
        <output aria-label={label} aria-live="polite">
          {value}
        </output>
        <IconButton
          size="small"
          aria-label={`Increase ${label.toLowerCase()}`}
          disabled={value >= max}
          onClick={() => onChange(value + 1)}
        >
          <AddRounded fontSize="small" />
        </IconButton>
      </div>
    </div>
  );
}
function SummaryRow({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="summary-row">
      <span className="summary-icon">{icon}</span>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}
function TravelLeg({
  mode,
  transit,
  driving,
  onMode,
  onTransit,
}: {
  mode: Stop["mode"];
  transit: number;
  driving: boolean;
  onMode: (v: Stop["mode"]) => void;
  onTransit: (n: number) => void;
}) {
  return (
    <div className="field-grid two">
      <TextField
        select
        label="Travel by"
        disabled={driving}
        value={mode}
        onChange={(e) => onMode(e.target.value as Stop["mode"])}
      >
        <MenuItem value="flight">Flight</MenuItem>
        <MenuItem value="train">Train</MenuItem>
        <MenuItem value="drive">Drive</MenuItem>
      </TextField>
      <TextField
        select
        label="Nights in transit"
        helperText="Overnight travel counts toward your dates"
        value={transit}
        onChange={(e) => onTransit(+e.target.value)}
      >
        {[0, 1, 2, 3].map((n) => (
          <MenuItem key={n} value={n}>
            {n === 0 ? "Same-day arrival" : `${n} night${n > 1 ? "s" : ""}`}
          </MenuItem>
        ))}
      </TextField>
    </div>
  );
}
function FlightFields({
  value,
  onChange,
}: {
  value: FlightPreferences;
  onChange: (value: FlightPreferences) => void;
}) {
  return (
    <Stack spacing={2} sx={{ mt: 2 }}>
      <TextField
        select
        label="Flight stops"
        value={value.max_stops}
        onChange={(e) => onChange({ ...value, max_stops: +e.target.value })}
      >
        <MenuItem value={0}>Nonstop only</MenuItem>
        <MenuItem value={1}>Up to 1 stop</MenuItem>
        <MenuItem value={2}>Up to 2 stops</MenuItem>
      </TextField>
      <div className="field-grid two">
        <TextField
          label="Depart after (optional)"
          type="time"
          value={value.earliest_departure ?? ""}
          slotProps={{ inputLabel: { shrink: true } }}
          onChange={(e) =>
            onChange({ ...value, earliest_departure: e.target.value || null })
          }
        />
        <TextField
          label="Arrive before (optional)"
          type="time"
          value={value.latest_arrival ?? ""}
          slotProps={{ inputLabel: { shrink: true } }}
          onChange={(e) =>
            onChange({ ...value, latest_arrival: e.target.value || null })
          }
        />
      </div>
      <FormControlLabel
        control={
          <Checkbox
            checked={value.allow_overnight}
            onChange={(e) =>
              onChange({ ...value, allow_overnight: e.target.checked })
            }
          />
        }
        label="Overnight flights are okay"
      />
      <Typography variant="caption" color="text.secondary">
        Times are local to each airport. Confirm these preferences when booking.
      </Typography>
    </Stack>
  );
}
