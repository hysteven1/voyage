
"use client";

import { FormEvent, useState } from "react";

type TripForm = {
  origin: string;
  destination: string;
  start_date: string;
  end_date: string;
  travelers: number;
  budget: number;
  preferences: string[];
};

const PREFERENCES = [
  "Food",
  "Nature",
  "Culture",
  "Adventure",
  "Relaxation",
];

export default function Home() {
  const [form, setForm] = useState<TripForm>({
    origin: "",
    destination: "",
    start_date: "",
    end_date: "",
    travelers: 2,
    budget: 3000,
    preferences: [],
  });

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function updateField<K extends keyof TripForm>(
    key: K,
    value: TripForm[K]
  ) {
    setForm((previous) => ({
      ...previous,
      [key]: value,
    }));
  }

  function togglePreference(preference: string) {
    setForm((previous) => ({
      ...previous,
      preferences: previous.preferences.includes(preference)
        ? previous.preferences.filter((p) => p !== preference)
        : [...previous.preferences, preference],
    }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/trips`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(form),
        }
      );

      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }

      const data = await response.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Something went wrong"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-16 text-white">
      <div className="mx-auto max-w-2xl">
        <div className="mb-10">
          <p className="mb-2 text-sm font-semibold uppercase tracking-widest text-sky-400">
            Voyage
          </p>
          <h1 className="text-4xl font-bold tracking-tight">
            Plan your next adventure
          </h1>
          <p className="mt-3 text-slate-400">
            Tell us where you want to go. We&apos;ll help you
            create a personalized itinerary within your budget.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="space-y-6 rounded-2xl border border-slate-800 bg-slate-900 p-8"
        >
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Origin">
              <input
                required
                value={form.origin}
                onChange={(e) =>
                  updateField("origin", e.target.value)
                }
                placeholder="Washington, DC"
                className="input"
              />
            </Field>

            <Field label="Destination">
              <input
                required
                value={form.destination}
                onChange={(e) =>
                  updateField("destination", e.target.value)
                }
                placeholder="Tokyo, Japan"
                className="input"
              />
            </Field>

            <Field label="Start date">
              <input
                required
                type="date"
                value={form.start_date}
                onChange={(e) =>
                  updateField("start_date", e.target.value)
                }
                className="input"
              />
            </Field>

            <Field label="End date">
              <input
                required
                type="date"
                min={form.start_date || undefined}
                value={form.end_date}
                onChange={(e) =>
                  updateField("end_date", e.target.value)
                }
                className="input"
              />
            </Field>

            <Field label="Travelers">
              <input
                required
                type="number"
                min={1}
                max={20}
                value={form.travelers}
                onChange={(e) =>
                  updateField("travelers", Number(e.target.value))
                }
                className="input"
              />
            </Field>

            <Field label="Total budget (USD)">
              <input
                required
                type="number"
                min={1}
                value={form.budget}
                onChange={(e) =>
                  updateField("budget", Number(e.target.value))
                }
                className="input"
              />
            </Field>
          </div>

          <fieldset>
            <legend className="mb-3 text-sm font-medium text-slate-300">
              What are you interested in?
            </legend>

            <div className="flex flex-wrap gap-2">
              {PREFERENCES.map((preference) => {
                const selected = form.preferences.includes(preference);

                return (
                  <button
                    key={preference}
                    type="button"
                    onClick={() => togglePreference(preference)}
                    aria-pressed={selected}
                    className={`rounded-full border px-4 py-2 text-sm transition ${
                      selected
                        ? "border-sky-400 bg-sky-400/15 text-sky-300"
                        : "border-slate-700 text-slate-300 hover:border-slate-500"
                    }`}
                  >
                    {preference}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-sky-500 px-5 py-3 font-semibold text-slate-950 transition hover:bg-sky-400 disabled:opacity-50"
          >
            {loading ? "Submitting..." : "Create trip"}
          </button>

          {error && (
            <p role="alert" className="text-sm text-red-400">
              {error}
            </p>
          )}
        </form>

        {result && (
          <section className="mt-8 rounded-2xl border border-emerald-800 bg-emerald-950/30 p-6">
            <h2 className="mb-3 font-semibold text-emerald-300">
              Trip request accepted
            </h2>
            <pre className="overflow-x-auto text-sm text-slate-300">
              {result}
            </pre>
          </section>
        )}
      </div>
    </main>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-2">
      <span className="text-sm font-medium text-slate-300">
        {label}
      </span>
      {children}
    </label>
  );
}
