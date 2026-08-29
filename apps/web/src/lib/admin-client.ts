export function readCsrfCookie(): string | null {
  const prefix = "bukky_admin_csrf=";
  const value = document.cookie.split("; ").find((part) => part.startsWith(prefix));
  return value ? decodeURIComponent(value.slice(prefix.length)) : null;
}
