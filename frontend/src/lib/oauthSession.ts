/**
 * Remembers the sign-in attempt across the redirect to the platform and back.
 * The `state` kept here must match the one the platform returns; that is what
 * stops someone else's sign-in link from being completed in this browser.
 */
const KEY = "sr_oauth";

export interface OAuthSession {
  state: string;
  slug: string;
}

export function saveOAuthSession(session: OAuthSession): void {
  sessionStorage.setItem(KEY, JSON.stringify(session));
}

export function readOAuthSession(): OAuthSession | null {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(KEY) ?? "null");
    return parsed && typeof parsed.state === "string" && typeof parsed.slug === "string" ? parsed : null;
  } catch {
    return null;
  }
}

export function clearOAuthSession(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    /* storage unavailable */
  }
}
