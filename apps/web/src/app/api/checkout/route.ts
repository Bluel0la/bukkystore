const MAX_CHECKOUT_BYTES = 20_000;

export async function POST(request: Request) {
  const contentLength = Number(request.headers.get("content-length") ?? "0");
  if (contentLength > MAX_CHECKOUT_BYTES) {
    return Response.json({ message: "The checkout request is too large." }, { status: 413 });
  }
  const body = await request.text();
  if (new TextEncoder().encode(body).byteLength > MAX_CHECKOUT_BYTES) {
    return Response.json({ message: "The checkout request is too large." }, { status: 413 });
  }
  const baseUrl = (process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
  try {
    const response = await fetch(`${baseUrl}/api/v1/checkout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": request.headers.get("idempotency-key") ?? "",
      },
      body,
      cache: "no-store",
    });
    return new Response(await response.text(), {
      status: response.status,
      headers: { "Content-Type": response.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return Response.json({ message: "Checkout is temporarily unavailable." }, { status: 503 });
  }
}
