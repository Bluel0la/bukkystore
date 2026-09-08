const ALLOWED_PARAMS = new Set(["category", "available", "featured", "limit"]);

export async function GET(request: Request) {
  const incoming = new URL(request.url).searchParams;
  const outgoing = new URLSearchParams();
  for (const [key, value] of incoming) {
    if (ALLOWED_PARAMS.has(key) && value) outgoing.set(key, value);
  }
  if (!outgoing.has("limit")) outgoing.set("limit", "8");
  const baseUrl = (process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
  try {
    const response = await fetch(`${baseUrl}/api/v1/products?${outgoing}`, {
      headers: { accept: "application/json" },
      cache: "no-store",
    });
    return new Response(await response.text(), {
      status: response.status,
      headers: { "Content-Type": response.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return Response.json({ message: "The catalogue is temporarily unavailable." }, { status: 503 });
  }
}
