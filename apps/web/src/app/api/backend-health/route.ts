import { NextResponse } from "next/server";

const apiUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

export async function GET() {
  try {
    const response = await fetch(`${apiUrl}/api/v1/health/live`, {
      cache: "no-store",
      signal: AbortSignal.timeout(2_000),
    });
    if (!response.ok) throw new Error("API health check failed");

    return NextResponse.json({ status: "connected" });
  } catch {
    return NextResponse.json({ status: "unavailable" }, { status: 503 });
  }
}
