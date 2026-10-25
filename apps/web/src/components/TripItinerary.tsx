"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Alert,
  Button,
  CircularProgress,
  LinearProgress,
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

export default function TripItinerary({
  tripId,
  autoStart = false,
}: {
  tripId: string;
  autoStart?: boolean;
}) {
  const [status, setStatus] = useState("draft");
  const [plan, setPlan] = useState<LegacyPlan | ExpandedPlan | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<{
    label: string;
    percent: number | null;
  }>({ label: "Getting your trip ready", percent: null });
  const [elapsed, setElapsed] = useState(0);
  const generation = useRef(0);
  const startPlanning = useCallback(async () => {
    const run = ++generation.current;
    setLoading(true);
    setError("");
    setProgress({ label: "Getting your trip ready", percent: null });
    setElapsed(0);
    try {
      await api(`/api/v1/trips/${tripId}/plan`, {});
      if (generation.current !== run) return;
      setStatus("planning");
      for (let attempt = 0; attempt < 600; attempt++) {
        const trip = await api<{ status: string; planning_error?: string }>(
          `/api/v1/trips/${tripId}`,
        );
        if (generation.current !== run) return;
        setStatus(trip.status);
        if (trip.status === "planning" && attempt % 2 === 0) {
          const update = await api<{ label: string; percent: number | null }>(
            `/api/v1/trips/${tripId}/progress`,
          ).catch(() => null);
          if (generation.current !== run) return;
          if (update?.label) setProgress(update);
        }
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
  }, [tripId]);

  useEffect(() => {
    if (!loading) return;
    const timer = setInterval(() => setElapsed((seconds) => seconds + 1), 1000);
    return () => clearInterval(timer);
  }, [loading]);

  useEffect(() => {
    let active = true;
    if (autoStart)
      queueMicrotask(() => {
        if (active) void startPlanning();
      });
    return () => {
      active = false;
      generation.current += 1;
    };
  }, [autoStart, startPlanning]);

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
            {loading ? "Building your itinerary" : "Ready to plan"}
          </Typography>
        </Stack>
        <Typography variant="body2" color="text.secondary">
          {loading
            ? "We’re putting together your route, stays, and daily ideas. This can take a few minutes."
            : "We’ll turn your route into a thoughtful day-by-day itinerary, with estimated costs and searches to help you book."}
        </Typography>
        {loading && (
          <Stack
            spacing={1.5}
            sx={{ width: "100%" }}
            role="status"
            aria-live="polite"
          >
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {progress.label}
            </Typography>
            <LinearProgress
              aria-label="Trip planning progress"
              variant={
                progress.percent == null ? "indeterminate" : "determinate"
              }
              value={progress.percent ?? undefined}
              sx={{ height: 8, borderRadius: 4 }}
            />
            <Typography variant="caption" color="text.secondary">
              {Math.floor(elapsed / 60)}:{String(elapsed % 60).padStart(2, "0")}{" "}
              elapsed · Longer trips can take a few minutes. You can keep this
              page open while we plan.
            </Typography>
          </Stack>
        )}
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
