"use client";

import { useState } from "react";

type Activity = {
  id: string;
  name: string;
  category: string;
  price_per_person: string;
  duration_hours: number;
};

type DayNarrative = {
  date: string;
  description: string;
  travel_tip: string;
};

type TripNarrative = {
  title: string;
  summary: string;
  source: "openai" | "fallback";
  days: DayNarrative[];
};

type Itinerary = {
  narrative?: TripNarrative;
  trip_id: string;
  data_source: string;
  currency: string;
  flight: {
    provider: string;
    price: string;
  };
  hotel: {
    name: string;
    price_per_night: string;
  };
  days: {
    date: string;
    activities: Activity[];
  }[];
  budget: {
    limit: string;
    flight: string;
    hotel: string;
    activities: string;
    total: string;
    remaining: string;
  };
};

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function TripItinerary({
  tripId,
}: {
  tripId: string;
}) {
  const [status, setStatus] = useState("draft");
  const [plan, setPlan] = useState<Itinerary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function startPlanning() {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_URL}/api/v1/trips/${tripId}/plan`,
        { method: "POST" }
      );

      if (!response.ok) {
        throw new Error(`Planning request failed: ${response.status}`);
      }

      setStatus("planning");
      await pollUntilFinished();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Planning failed"
      );
    } finally {
      setLoading(false);
    }
  }

  async function pollUntilFinished() {
    for (let attempt = 0; attempt < 60; attempt++) {
      const response = await fetch(
        `${API_URL}/api/v1/trips/${tripId}`,
        { cache: "no-store" }
      );

      if (!response.ok) {
        throw new Error("Unable to check trip status");
      }

      const trip = await response.json();
      setStatus(trip.status);

      if (trip.status === "completed") {
        const planResponse = await fetch(
          `${API_URL}/api/v1/trips/${tripId}/itinerary`
        );

        if (!planResponse.ok) {
          throw new Error("Unable to retrieve itinerary");
        }

        setPlan(await planResponse.json());
        return;
      }

      if (trip.status === "failed") {
        throw new Error("Trip planning failed");
      }

      await new Promise((resolve) => setTimeout(resolve, 2000));
    }

    throw new Error(
      "Planning is still running. Refresh and check again."
    );
  }

  return (
    <section className="mt-8 space-y-6">
      {!plan && (
        <div className="rounded-xl border border-slate-700 p-6">
          <p className="mb-4 text-slate-300">
            Planning status: <strong>{status}</strong>
          </p>

          <button
            onClick={startPlanning}
            disabled={loading}
            className="rounded-lg bg-sky-500 px-5 py-3 font-semibold text-slate-950 disabled:opacity-50"
          >
            {loading ? "Generating itinerary..." : "Generate itinerary"}
          </button>

          {error && (
            <p role="alert" className="mt-3 text-red-400">
              {error}
            </p>
          )}
        </div>
      )}

      {plan && (
        <div className="space-y-6">
          <div className="rounded-xl border border-emerald-800 bg-emerald-950/20 p-6">
            <h2 className="text-2xl font-bold">
              Your Voyage itinerary
            </h2>
            <p className="mt-2 text-sm text-amber-300">
              Demo only — synthetic travel options and prices.
              No reservations have been made.
            </p>

            <p className="mt-4">
              Total estimated cost:{" "}
              <strong>${plan.budget.total}</strong>
            </p>
            <p>
              Remaining budget:{" "}
              <strong>${plan.budget.remaining}</strong>
            </p>
          </div>

          {plan.narrative && (
            <div className="rounded-xl border border-sky-800 bg-sky-950/20 p-6">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-sky-400">
                {plan.narrative.source === "openai"
                  ? "AI-personalized itinerary"
                  : "Standard itinerary"}
              </p>
              <h2 className="text-2xl font-bold">
                {plan.narrative.title}
              </h2>
              <p className="mt-3 text-slate-300">
                {plan.narrative.summary}
              </p>
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-700 p-5">
              <h3 className="font-semibold">Flight</h3>
              <p className="mt-2">{plan.flight.provider}</p>
              <p className="text-slate-400">
                ${plan.flight.price} per traveler
              </p>
            </div>

            <div className="rounded-xl border border-slate-700 p-5">
              <h3 className="font-semibold">Hotel</h3>
              <p className="mt-2">{plan.hotel.name}</p>
              <p className="text-slate-400">
                ${plan.hotel.price_per_night} per night
              </p>
            </div>
          </div>

          <h3 className="text-xl font-bold">Daily itinerary</h3>

          {plan.days.map((day) => (
            <div
              key={day.date}
              className="rounded-xl border border-slate-700 p-5"
            >
              <h4 className="font-semibold">{day.date}</h4>

              {day.activities.length === 0 ? (
                <p className="mt-2 text-slate-400">
                  Free time / explore independently
                </p>
              ) : (
                day.activities.map((activity) => (
                  <div key={activity.id} className="mt-3">
                    <p>{activity.name}</p>
                    <p className="text-sm text-slate-400">
                      {activity.duration_hours} hours ·{" "}
                      ${activity.price_per_person} per person
                    </p>
                  </div>
                ))
              )}

              {(() => {
                const narrative = plan.narrative?.days.find(
                  (item) => item.date === day.date
                );

                if (!narrative) return null;

                return (
                  <div className="mt-4 border-t border-slate-700 pt-4">
                    <p className="text-sm text-slate-300">
                      {narrative.description}
                    </p>
                    <p className="mt-2 text-sm text-sky-300">
                      Tip: {narrative.travel_tip}
                    </p>
                  </div>
                );
              })()}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
