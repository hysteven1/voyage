"use client";

import { FormEvent, ReactNode, useEffect, useRef, useState } from "react";
import dayjs from "dayjs";
import Link from "next/link";
import {
  Alert,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Divider,
  FormControlLabel,
  FormControl,
  FormLabel,
  Radio,
  RadioGroup,
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
import CheckRounded from "@mui/icons-material/CheckRounded";
import HotelRounded from "@mui/icons-material/HotelRounded";
import SpaRounded from "@mui/icons-material/SpaRounded";
import ParkRounded from "@mui/icons-material/ParkRounded";
import MuseumRounded from "@mui/icons-material/MuseumRounded";
import HikingRounded from "@mui/icons-material/HikingRounded";
import AttractionsRounded from "@mui/icons-material/AttractionsRounded";
import ShoppingBagRounded from "@mui/icons-material/ShoppingBagRounded";
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
  { name: "Iconic sights", icon: <LocationOnRounded /> },
  { name: "Culture & history", icon: <MuseumRounded /> },
  { name: "Nature & scenery", icon: <ParkRounded /> },
  { name: "Adventure & hiking", icon: <HikingRounded /> },
  { name: "Shopping", icon: <ShoppingBagRounded /> },
  { name: "Theme parks", icon: <AttractionsRounded /> },
  { name: "Day trips", icon: <ExploreRounded /> },
];
const initial: TripForm = {
  origin: "",
  start_date: "",
  end_date: "",
  travelers: 2,
  budget: null,
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
    budget_basis: "per_person",
    spending_style: "value",
    budget_enforcement: "target",
    flight_preferences: flightDefaults,
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
  useEffect(() => {
    if (["#how-it-works", "#planner"].includes(window.location.hash)) {
      window.history.replaceState(
        window.history.state,
        "",
        window.location.pathname + window.location.search,
      );
      window.scrollTo(0, 0);
    }
  }, []);
  const [form, setForm] = useState(initial);
  const [step, setStep] = useState(0);
  const [tripId, setTripId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [attempted, setAttempted] = useState(false);
  const [budgetInputInvalid, setBudgetInputInvalid] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const o = form.options;
  const field = <K extends keyof TripForm>(key: K, value: TripForm[K]) => {
    setError("");
    setForm((old) => ({ ...old, [key]: value }));
  };
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
  const people = o.adults + o.child_ages.length;
  const originInvalid =
    o.journey !== "already_there" && (form.origin?.trim().length ?? 0) < 2;
  const destinationNames = o.route.map((stop) =>
    stop.location.trim().toLowerCase(),
  );
  const destinationInvalid = destinationNames.map(
    (name) =>
      name.length < 2 ||
      destinationNames.indexOf(name) !== destinationNames.lastIndexOf(name),
  );
  const datesInvalid =
    !form.start_date || !form.end_date || nights < 1 || nights > 90;
  const budgetInvalid =
    budgetInputInvalid ||
    (form.budget !== null &&
      (!Number.isFinite(form.budget) ||
        form.budget <= 0 ||
        form.budget > 9999999999.99));

  function focusInvalid(formElement: HTMLFormElement) {
    requestAnimationFrame(() => {
      const invalid = formElement.querySelector<HTMLElement>(
        '[aria-invalid="true"]',
      );
      invalid?.focus();
      invalid?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }

  function navigate(next: number) {
    setStep(next);
    setError("");
    setAttempted(false);
    requestAnimationFrame(() => {
      heading.current?.focus();
      document
        .getElementById("planner")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setAttempted(true);
    if (step === 0) {
      if (originInvalid || datesInvalid || destinationInvalid.some(Boolean)) {
        focusInvalid(event.currentTarget);
        return;
      }
      navigate(1);
      return;
    }
    if (budgetInvalid) {
      focusInvalid(event.currentTarget);
      return;
    }
    setLoading(true);
    const options: Options = {
      ...o,
      endpoint: o.journey === "already_there" ? "one_way" : "return",
      end_location: null,
      route: o.route.map((stop) => ({
        ...stop,
        flight_preferences: o.flight_preferences ?? flightDefaults,
      })),
      return_flight_preferences: o.flight_preferences ?? flightDefaults,
    };
    const payload = {
      ...form,
      options,
      origin:
        o.journey === "already_there" ? null : form.origin?.trim() || null,
      travelers: people,
    };
    try {
      const suggested = await api<Proposal>(
        "/api/v1/trips/route-proposal",
        payload,
      );
      if (suggested.conflicts.length) {
        setError(
          `Please adjust these details: ${suggested.conflicts.join("; ")}`,
        );
        return;
      }
      const result = await api<{ id: string }>("/api/v1/trips", {
        ...payload,
        options: suggested.options,
      });
      setForm((old) => ({ ...old, options: suggested.options }));
      setTripId(result.id);
      requestAnimationFrame(() =>
        document
          .getElementById("planner")
          ?.scrollIntoView({ behavior: "smooth" }),
      );
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

  return (
    <div className="voyage-site">
      <header className="site-header">
        <Link className="wordmark" href="/" aria-label="Voyage home">
          <span className="brand-icon">
            <ExploreRounded />
          </span>
          voyage<span className="brand-dot">.</span>
        </Link>
        <span className="header-note">Less planning. A lot more living.</span>
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
                noValidate
                className="planner-card"
                aria-busy={loading}
              >
                <Stepper
                  activeStep={step}
                  alternativeLabel
                  className="planner-stepper"
                >
                  {["The essentials", "Your travel style"].map((label) => (
                    <Step key={label}>
                      <StepLabel>{label}</StepLabel>
                    </Step>
                  ))}
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
                      ][step]
                    }
                  </Typography>
                  <Typography color="text.secondary" sx={{ mt: 1 }}>
                    {
                      [
                        "Start with the big picture. We’ll help with the little details.",
                        "The best itineraries start with what matters to you.",
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
                        {o.journey !== "already_there" && (
                          <LocationAutocomplete
                            label="From"
                            error={attempted && originInvalid}
                            value={form.origin ?? ""}
                            required
                            onChange={(value) => field("origin", value)}
                            placeholder="Start typing a city, e.g. New York"
                            citiesOnly
                          />
                        )}
                        <div className="destinations-list">
                          {o.route.map((s, i) => (
                            <div
                              className={`destination-row ${o.route.length > 1 ? "removable" : ""}`}
                              key={i}
                            >
                              <span className="stop-number">
                                {String(i + 1).padStart(2, "0")}
                              </span>
                              <LocationAutocomplete
                                label={
                                  o.route.length > 1
                                    ? `Destination ${i + 1}`
                                    : o.journey === "already_there"
                                      ? "Where"
                                      : "Where to?"
                                }
                                value={s.location}
                                error={attempted && destinationInvalid[i]}
                                required
                                onChange={(value) =>
                                  updateStop(i, { location: value })
                                }
                                placeholder="Try Tokyo, Japan…"
                              />
                              {o.route.length > 1 && (
                                <IconButton
                                  aria-label={`Remove destination ${i + 1}`}
                                  onClick={() =>
                                    option(
                                      "route",
                                      o.route.filter((_, n) => n !== i),
                                    )
                                  }
                                >
                                  <DeleteOutlineRounded />
                                </IconButton>
                              )}
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
                      {o.journey === "flying" && (
                        <FormSection
                          title="How do you like to fly?"
                          subtitle="We’ll use these preferences for flight searches throughout your trip."
                        >
                          <FlightFields
                            value={o.flight_preferences ?? flightDefaults}
                            onChange={(value) =>
                              option("flight_preferences", value)
                            }
                          />
                        </FormSection>
                      )}
                      <FormSection title="Clear your calendar.">
                        <TravelDates
                          error={attempted && !!datesInvalid}
                          alreadyThere={o.journey === "already_there"}
                          start={form.start_date}
                          end={form.end_date}
                          onChange={(start, end) => {
                            setError("");
                            setForm((old) => ({
                              ...old,
                              start_date: start,
                              end_date: end,
                            }));
                          }}
                        />
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
                        title="What feels right for your trip?"
                        subtitle="Choose a spending style. Add a target if you have one, or leave the amount open."
                      >
                        <div className="choice-grid three">
                          {[
                            {
                              value: "budget",
                              title: "Budget conscious",
                              subtitle: "Keep costs down",
                            },
                            {
                              value: "value",
                              title: "Good value",
                              subtitle:
                                "Comfort, convenience & worthwhile experiences",
                            },
                            {
                              value: "upscale",
                              title: "Upscale",
                              subtitle: "More comfort and room for extras",
                            },
                          ].map((style) => (
                            <Choice
                              key={style.value}
                              selected={o.spending_style === style.value}
                              title={style.title}
                              subtitle={style.subtitle}
                              onClick={() =>
                                option(
                                  "spending_style",
                                  style.value as Options["spending_style"],
                                )
                              }
                            />
                          ))}
                        </div>
                        <div className="field-grid two">
                          <TextField
                            select
                            label="Budget for"
                            value={o.budget_basis ?? "per_person"}
                            onChange={(e) =>
                              option(
                                "budget_basis",
                                e.target.value as Options["budget_basis"],
                              )
                            }
                          >
                            <MenuItem value="per_person">Per person</MenuItem>
                            <MenuItem value="group">Whole group</MenuItem>
                          </TextField>
                          <TextField
                            label={
                              o.budget_basis === "group"
                                ? "Group target · USD (optional)"
                                : "Target per person · USD (optional)"
                            }
                            type="number"
                            name="budget"
                            error={attempted && budgetInvalid}
                            value={form.budget ?? ""}
                            slotProps={{
                              htmlInput: {
                                min: 0.01,
                                max: 9999999999.99,
                                step: "0.01",
                              },
                            }}
                            onChange={(e) => {
                              setBudgetInputInvalid(!e.target.validity.valid);
                              field(
                                "budget",
                                e.target.value === "" ? null : +e.target.value,
                              );
                            }}
                          />
                        </div>
                        <Typography variant="body2" color="text.secondary">
                          Per person works well for friends; a group target
                          works well for families. Estimates include transport,
                          stays, food and activities. Individual spending can
                          vary.
                        </Typography>
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
                        title="What would you love to explore? (optional)"
                        subtitle="Choose your interests, or leave it open for a mix of must-see highlights."
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
                            Open to hotels & vacation rentals
                          </MenuItem>
                          <MenuItem value="hotel">Hotels</MenuItem>
                          <MenuItem value="apartment">
                            Vacation rentals
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
                    disabled={loading}
                  >
                    {loading
                      ? "Finding your way…"
                      : ["Make it personal", "Plan my trip"][step]}
                  </Button>
                </div>
              </Paper>
            ) : (
              <>
                <Paper className="saved-card">
                  <Typography
                    component="h2"
                    variant="h4"
                    sx={{ fontWeight: 600 }}
                  >
                    Your itinerary
                  </Typography>
                  <Typography color="text.secondary" sx={{ mt: 1, mb: 2.5 }}>
                    Your travel, stays, and days ahead, all in one place.
                  </Typography>
                  <Stack direction="row" sx={{ gap: 1, flexWrap: "wrap" }}>
                    <Button
                      variant="outlined"
                      startIcon={<ArrowBackRounded />}
                      onClick={() => {
                        setTripId(null);
                        navigate(0);
                      }}
                    >
                      Edit trip details
                    </Button>
                    <Button
                      startIcon={<AddRounded />}
                      onClick={() => {
                        setTripId(null);
                        setForm(initial);
                        navigate(0);
                      }}
                    >
                      Plan another trip
                    </Button>
                  </Stack>
                </Paper>
                <TripItinerary key={tripId} tripId={tripId} autoStart />
              </>
            )}
          </div>
          <aside className="trip-sidebar" aria-label="Live trip snapshot">
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
                  label="Your route"
                  value={
                    [
                      ...(o.journey !== "already_there" && form.origin?.trim()
                        ? [form.origin.trim()]
                        : []),
                      ...o.route.map((s) => s.location.trim()),
                    ]
                      .filter(Boolean)
                      .join(" → ") || "Where will you go?"
                  }
                />
                <SummaryRow
                  icon={<ExploreRounded />}
                  label="Your dates"
                  value={
                    form.start_date && form.end_date
                      ? `${dayjs(form.start_date).format("MMM D")} – ${dayjs(form.end_date).format("MMM D")} · ${nights} nights`
                      : "Choose your travel dates"
                  }
                />
                {step > 0 && (
                  <>
                    <SummaryRow
                      icon={<HotelRounded />}
                      label="Your company"
                      value={`${people} traveler${people !== 1 ? "s" : ""} · ${o.rooms} room${o.rooms !== 1 ? "s" : ""}`}
                    />
                    <SummaryRow
                      icon={<SpaRounded />}
                      label="Your pace"
                      value={
                        {
                          relaxed: "Slow & easy",
                          balanced: "A little of everything",
                          busy: "See it all",
                        }[o.pace]
                      }
                    />
                    {form.preferences.length > 0 && (
                      <SummaryRow
                        icon={<ParkRounded />}
                        label="Your interests"
                        value={form.preferences.join(" · ")}
                      />
                    )}
                  </>
                )}
              </Stack>
            </div>
            <p className="sidebar-footnote">
              {step === 0
                ? "Up next: your people, your pace, and the things you love."
                : "We’ll work out the route and nights, and keep arrival days easy."}
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
function FlightFields({
  value,
  onChange,
}: {
  value: FlightPreferences;
  onChange: (value: FlightPreferences) => void;
}) {
  return (
    <Stack spacing={2.5}>
      <FormControl>
        <FormLabel id="flight-stops-label">Connections</FormLabel>
        <RadioGroup
          row
          aria-labelledby="flight-stops-label"
          value={value.max_stops === 0 ? "nonstop" : "connections"}
          onChange={(e) =>
            onChange({
              ...value,
              max_stops: e.target.value === "nonstop" ? 0 : 1,
            })
          }
        >
          <FormControlLabel
            value="nonstop"
            control={<Radio />}
            label="Nonstop only"
          />
          <FormControlLabel
            value="connections"
            control={<Radio />}
            label="Up to one stop is okay"
          />
        </RadioGroup>
      </FormControl>
      <FormControl>
        <FormLabel id="overnight-label">Overnight flights</FormLabel>
        <RadioGroup
          row
          aria-labelledby="overnight-label"
          value={value.allow_overnight ? "yes" : "no"}
          onChange={(e) =>
            onChange({ ...value, allow_overnight: e.target.value === "yes" })
          }
        >
          <FormControlLabel
            value="no"
            control={<Radio />}
            label="No overnight flights"
          />
          <FormControlLabel
            value="yes"
            control={<Radio />}
            label="Overnight is okay"
          />
        </RadioGroup>
      </FormControl>
      <div className="field-grid two">
        <TextField
          label="Depart after (optional)"
          type="time"
          value={value.earliest_departure ?? ""}
          slotProps={{
            inputLabel: { shrink: true },
            input: {
              onClick: (event) => {
                const input = event.currentTarget.querySelector("input");
                try {
                  input?.showPicker?.();
                } catch {
                  /* Keyboard entry remains available if the browser cannot open its picker. */
                }
              },
            },
          }}
          onChange={(e) =>
            onChange({ ...value, earliest_departure: e.target.value || null })
          }
        />
        <TextField
          label="Arrive before (optional)"
          type="time"
          value={value.latest_arrival ?? ""}
          slotProps={{
            inputLabel: { shrink: true },
            input: {
              onClick: (event) => {
                const input = event.currentTarget.querySelector("input");
                try {
                  input?.showPicker?.();
                } catch {
                  /* Keyboard entry remains available if the browser cannot open its picker. */
                }
              },
            },
          }}
          onChange={(e) =>
            onChange({ ...value, latest_arrival: e.target.value || null })
          }
        />
      </div>
      <Typography variant="caption" color="text.secondary">
        Times are local to each airport. Confirm these preferences when booking.
      </Typography>
    </Stack>
  );
}
