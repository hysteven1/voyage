// Keep browser requests on the web origin. Only the server knows the API address.
async function proxy(request: Request) {
  const incoming = new URL(request.url);
  const upstream = new URL(process.env.API_INTERNAL_URL ?? "http://localhost:8000");
  upstream.pathname = incoming.pathname;
  upstream.search = incoming.search;
  try {
    const response = await fetch(upstream, {
      method: request.method,
      headers: { "Content-Type": "application/json" },
      body: request.method === "POST" ? await request.arrayBuffer() : undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(55_000),
      redirect: "error",
    });
    const headers = new Headers({ "Cache-Control": "no-store" });
    for (const key of ["Content-Type", "X-Request-ID"]) {
      const value = response.headers.get(key);
      if (value) headers.set(key, value);
    }
    return new Response(response.body, { status: response.status, headers });
  } catch {
    return Response.json(
      { detail: "The trip service is unavailable. Please try again." },
      { status: 502 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
