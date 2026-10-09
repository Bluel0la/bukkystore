type ErrorDetail = {
  location?: Array<string | number>;
  message?: string;
};

type ErrorBody = {
  code?: string;
  message?: string;
  details?: ErrorDetail[];
};

const ACRONYMS: Record<string, string> = { sku: "SKU", id: "ID", url: "URL" };
const MAX_DETAILS = 3;

// Exact backend messages worth translating into plain language. Anything not
// listed falls through to the generic field-named pipeline below, so backend
// rewording degrades gracefully instead of breaking.
const KNOWN_MESSAGES: Record<string, string> = {
  "compare_at_price_minor must exceed base_price_minor":
    "Compare-at price must be higher than the selling price.",
};

function humanizeSegment(segment: string | number): string {
  if (typeof segment === "number") return `#${segment + 1}`;
  const cleaned = segment.replace(/_/g, " ").trim();
  if (!cleaned) return "";
  return ACRONYMS[cleaned.toLowerCase()] ?? cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

function humanizeLocation(location: Array<string | number> | undefined): string {
  if (!location || !location.length) return "";
  // Drop framework roots like "body" / "query" and empty segments.
  const parts = location.filter(
    (segment) => segment !== "body" && segment !== "query" && segment !== "",
  );
  if (!parts.length) return "";
  // "variants.0.sku" reads better as "Variants #1 · SKU".
  const head = parts.slice(0, -1).map(humanizeSegment).filter(Boolean).join(" ");
  const tail = humanizeSegment(parts[parts.length - 1] as string | number);
  return [head, tail].filter(Boolean).join(" · ");
}

function stripPrefix(message: string): string {
  return message.replace(/^(Value error|Assertion failed),\s*/i, "").trim();
}

function cleanMessage(message: string, fieldKey: string): string {
  let text = message;
  // Backends often repeat the field name up front ("compare_at_price_minor
  // must exceed ...") — the label already carries it.
  if (fieldKey && text.toLowerCase().startsWith(fieldKey.toLowerCase())) {
    text = text.slice(fieldKey.length).trimStart();
  }
  // Backend-isms leak through as snake_case; messages are sentences for humans.
  text = text.replace(/_/g, " ");
  return text.replace(/\s{2,}/g, " ").trim();
}

/** Extract cleaned, field-named messages from an API error body. */
export function apiErrorDetails(body: unknown): string[] {
  if (!body || typeof body !== "object") return [];
  const details = (body as ErrorBody).details;
  if (!Array.isArray(details)) return [];
  const messages: string[] = [];
  for (const detail of details.slice(0, MAX_DETAILS)) {
    if (!detail || typeof detail.message !== "string" || !detail.message.trim()) continue;
    const stripped = stripPrefix(detail.message);
    // Known translations stand alone — no field prefix needed.
    if (KNOWN_MESSAGES[stripped]) {
      messages.push(KNOWN_MESSAGES[stripped]);
      continue;
    }
    const segments = Array.isArray(detail.location) ? detail.location : [];
    const field = humanizeLocation(segments);
    const rawTail = [...segments].reverse().find((segment) => segment !== "body" && segment !== "query" && segment !== "");
    const text = cleanMessage(detail.message, typeof rawTail === "string" ? rawTail : "");
    if (!text) continue;
    messages.push(field ? `${field}: ${text}` : text);
  }
  return messages;
}

/**
 * Render an API failure for shoppers and admins: specific field messages
 * first, then the server message, then a safe fallback. Never leaks
 * stack traces, SQL, or correlation internals.
 */
export function formatApiError(body: unknown, fallback: string): string {
  const details = apiErrorDetails(body);
  if (details.length) return details.join(" · ");
  if (body && typeof body === "object") {
    const message = (body as ErrorBody).message;
    if (typeof message === "string" && message.trim()) return message.trim();
  }
  return fallback;
}
