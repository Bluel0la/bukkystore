const MAX_CONFIRMATION_BYTES = 1_000;

export async function POST(request: Request) {
  const body = await request.text();
  if (new TextEncoder().encode(body).byteLength > MAX_CONFIRMATION_BYTES) {
    return Response.json({ message: "The confirmation request is too large." }, { status: 413 });
  }
  const baseUrl = (process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
  try {
    const upstream = await fetch(`${baseUrl}/api/v1/payments/fake/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      cache: "no-store",
    });
    return new Response(await upstream.text(), {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return Response.json({ message: "Payment confirmation is temporarily unavailable." }, { status: 503 });
  }
}
