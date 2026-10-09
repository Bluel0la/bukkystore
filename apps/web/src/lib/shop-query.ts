export type ShopParams = Record<string, string | string[] | undefined>;

/** Bound public filters to the API contract; shoppers enter prices in naira. */
export function shopQuery(params: ShopParams) {
  const value = (key: string, max: number) => typeof params[key] === "string" ? params[key].trim().slice(0, max) : "";
  const query = new URLSearchParams({ limit: "12" });
  const category = value("category", 200);
  if (/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(category)) query.set("category", category);
  for (const [key, max] of [["search", 80], ["size", 40], ["cursor", 500]] as const) {
    const text = value(key, max);
    if (text) query.set(key, text);
  }
  if (value("available", 5) === "true") query.set("available", "true");
  const budget = Number(value("budget", 9));
  if (Number.isSafeInteger(budget) && budget > 0) query.set("max_price_minor", String(budget * 100));
  return query;
}

export function shopHref(query: URLSearchParams, changes: Record<string, string | null> = {}) {
  const next = new URLSearchParams(query);
  next.delete("limit");
  const minor = next.get("max_price_minor");
  next.delete("max_price_minor");
  if (minor) next.set("budget", String(Number(minor) / 100));
  for (const [key, value] of Object.entries(changes)) {
    if (value === null) next.delete(key);
    else next.set(key, value);
  }
  return `/${next.size ? `?${next}` : ""}#shop`;
}
