import type { NextRequest } from "next/server";

const allowedPath = /^(auth\/(login|logout|me)|categories(?:\/[0-9a-f-]+)?|products(?:\/bulk-archive|\/[0-9a-f-]+(?:\/(?:archive|unarchive|images(?:\/signatures|\/reorder|\/[0-9a-f-]+(?:\/alt-text)?)?))?)?|orders(?:\/[0-9a-f-]+(?:\/(transitions|cancellations))?)?|refunds\/[0-9a-f-]+\/complete|variants\/[0-9a-f-]+\/stock-adjustments|store-settings|delivery-areas(?:\/[0-9a-f-]+)?)$/;

async function proxy(request: NextRequest, context: RouteContext<"/api/admin/[...path]">) {
  const { path } = await context.params;
  const requestedPath = path.join("/");
  if (!allowedPath.test(requestedPath)) {
    return Response.json({ message: "Not found" }, { status: 404 });
  }
  const baseUrl = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";
  const target = new URL(`/api/v1/admin/${requestedPath}`, baseUrl);
  target.search = new URL(request.url).search;
  const headers = new Headers({ accept: "application/json" });
  for (const name of ["content-type", "cookie", "x-csrf-token", "idempotency-key"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  try {
    const upstream = await fetch(target, {
      signal: requestedPath === "auth/login" ? AbortSignal.timeout(15000) : undefined,
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.text(),
      cache: "no-store",
      redirect: "manual",
    });
    const responseHeaders = new Headers();
    const contentType = upstream.headers.get("content-type");
    if (contentType) responseHeaders.set("content-type", contentType);
    for (const cookie of upstream.headers.getSetCookie()) responseHeaders.append("set-cookie", cookie);
    const body = requestedPath === "auth/login" ? await upstream.arrayBuffer() : upstream.body;
    return new Response(body, { status: upstream.status, headers: responseHeaders });
  } catch (error) {
    if (error && typeof error === "object" && "name" in error && error.name === "TimeoutError") {
      return Response.json({ message: "Sign-in timed out. Please try again shortly." }, { status: 504 });
    }
    return Response.json({ message: "Admin service unavailable" }, { status: 503 });
  }
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
