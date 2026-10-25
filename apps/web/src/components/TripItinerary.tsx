"use client";

import { useEffect, useRef, useState } from "react";
import {
  Alert,
  Button,
  CircularProgress,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import AutoAwesomeRounded from "@mui/icons-material/AutoAwesomeRounded";
import ExpandedItinerary, {
  ExpandedPlan,
} from "@/components/ExpandedItinerary";
import { api } from "@/lib/trip";

type LegacyPlan = {
  version?: 1;
  narrative?: {
    title: string;
    summary: string;
    days: { date: string; description: string; travel_tip: string }[];
  };
  trip_id: string;
  flight: { provider: string; price: string };
  hotel: { name: string; price_per_night: string };
  days: {
    date: string;
    activities: {
      id: string;
      name: string;
      duration_hours: number;
      price_per_person: string;
    }[];
  }[];
  budget: { total: string; remaining: string };
};

export default function TripItinerary({ tripId }: { tripId: string }) {
  const [status, setStatus] = useState("draft");
  const [plan, setPlan] = useState<LegacyPlan | ExpandedPlan | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const generation = useRef(0);
  useEffect(
    () => () => {
      generation.current += 1;
    },
    [],
  );

  async function startPlanning() {
    const run = ++generation.current;
    setLoading(true);
    setError("");
    try {
      await api(`/api/v1/trips/${tripId}/plan`, {});
      if (generation.current !== run) return;
      setStatus("planning");
      for (let attempt = 0; attempt < 90; attempt++) {
        const trip = await api<{ status: string; planning_error?: string }>(
          `/api/v1/trips/${tripId}`,
        );
        if (generation.current !== run) return;
        setStatus(trip.status);
        if (trip.status === "completed") {
          const result = await api<LegacyPlan | ExpandedPlan>(
            `/api/v1/trips/${tripId}/itinerary`,
          );
          if (generation.current === run) setPlan(result);
          return;
        }
        // A retried workflow may not have updated a previously failed row yet.
        if (trip.status === "failed" && attempt >= 3)
          throw new Error(
            trip.planning_error ||
              "Planning couldn’t finish. Try again or adjust your trip details.",
          );
        await new Promise((resolve) => setTimeout(resolve, 2000));
        if (generation.current !== run) return;
      }
      throw new Error(
        "Your trip is still being planned. Select ‘Check again’ to pick up where you left off.",
      );
    } catch (e) {
      if (generation.current === run)
        setError(e instanceof Error ? e.message : "Unable to plan your trip");
    } finally {
      if (generation.current === run) setLoading(false);
    }
  }

  if (plan?.version === 2) return <ExpandedItinerary plan={plan} />;
  if (plan)
    return (
      <section className="itinerary-stack" aria-label="Your itinerary">
        <Paper className="itinerary-panel">
          <Typography component="h2" variant="h4">
            {plan.narrative?.title ?? "Your Voyage itinerary"}
          </Typography>
          <Typography color="text.secondary" sx={{ my: 2 }}>
            {plan.narrative?.summary}
          </Typography>
          <Alert severity="info">
            This saved itinerary uses sample options and prices. No reservations
            have been made.
          </Alert>
          <Typography sx={{ mt: 2 }}>
            Estimated group total: <strong>${plan.budget.total}</strong> ·
            Remaining: ${plan.budget.remaining}
          </Typography>
        </Paper>
        <Paper className="itinerary-panel">
          <Typography component="h3" className="itinerary-section-title">
            Travel & stay
          </Typography>
          <Typography>
            {plan.flight.provider} · ${plan.flight.price} per traveler
          </Typography>
          <Typography>
            {plan.hotel.name} · ${plan.hotel.price_per_night} per night
          </Typography>
        </Paper>
        {plan.days.map((day) => (
          <Paper component="article" key={day.date} className="itinerary-panel">
            <Typography component="h3" className="itinerary-section-title">
              {day.date}
            </Typography>
            {day.activities.length === 0 && (
              <Typography color="text.secondary">
                Free time to explore at your own pace.
              </Typography>
            )}
            {day.activities.map((activity) => (
              <div className="activity-row" key={activity.id}>
                <Typography>{activity.name}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {activity.duration_hours} hours · ${activity.price_per_person}{" "}
                  per person
                </Typography>
              </div>
            ))}
            {plan.narrative?.days.find((item) => item.date === day.date)
              ?.description && (
              <Typography variant="body2" sx={{ mt: 2 }} color="text.secondary">
                {
                  plan.narrative.days.find((item) => item.date === day.date)
                    ?.description
                }
              </Typography>
            )}
          </Paper>
        ))}
      </section>
    );
  return (
    <Paper className="itinerary-panel">
      <Stack spacing={2.5} sx={{ alignItems: "flex-start" }}>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
          {loading ? (
            <CircularProgress size={24} />
          ) : (
            <AutoAwesomeRounded color="primary" />
          )}
          <Typography variant="h6" component="h3">
            {loading ? "A little planning magic…" : "Ready when you are."}
          </Typography>
        </Stack>
        <Typography variant="body2" color="text.secondary">
          {loading
            ? "We’re putting together your route, stays, and daily ideas. This can take a few minutes."
            : "We’ll turn your route into a thoughtful day-by-day itinerary, with estimated costs and searches to help you book."}
        </Typography>
        <Button
          variant="contained"
          disabled={loading}
          onClick={startPlanning}
          startIcon={!loading && <AutoAwesomeRounded />}
        >
          {loading
            ? "Planning your trip…"
            : error
              ? status === "failed"
                ? "Try planning again"
                : "Check again"
              : "Create my itinerary"}
        </Button>
        {error && (
          <Alert severity="error" role="alert" sx={{ width: "100%" }}>
            {error}
          </Alert>
        )}
      </Stack>
    </Paper>
  );
}
