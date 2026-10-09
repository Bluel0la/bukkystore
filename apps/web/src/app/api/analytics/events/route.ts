const MAX_EVENT_BYTES = 4_000;

export async function POST(request: Request) {
  const contentLength = Number(request.headers.get("content-length") ?? "0");
  if (contentLength > MAX_EVENT_BYTES) {
    return Response.json({ message: "The analytics event is too large." }, { status: 413 });
  }
  const body = await request.text();
  if (new TextEncoder().encode(body).byteLength > MAX_EVENT_BYTES) {
    return Response.json({ message: "The analytics event is too large." }, { status: 413 });
  }
  const baseUrl = (process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
  const forwardedFor = request.headers.get("x-forwarded-for");
  try {
    const response = await fetch(`${baseUrl}/api/v1/analytics/events`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(forwardedFor ? { "X-Forwarded-For": forwardedFor } : {}),
      },
      body,
      cache: "no-store",
    });
    return new Response(await response.text(), {
      status: response.status,
      headers: { "Content-Type": response.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    // Analytics failures stay silent so tracking never breaks shopping.
    return Response.json({ message: "Analytics is temporarily unavailable." }, { status: 503 });
  }
}
