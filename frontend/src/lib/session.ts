export const TOKEN_KEY = "dealership.access-token";

// Expiry is a UX check only. The backend verifies signatures and supplies the authoritative role.
export function tokenExpiry(token: string): number | null {
  try {
    const encoded = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const claims = JSON.parse(
      atob(encoded.padEnd(Math.ceil(encoded.length / 4) * 4, "=")),
    );
    return typeof claims.exp === "number" && Number.isFinite(claims.exp)
      ? claims.exp * 1000
      : null;
  } catch {
    return null;
  }
}

export function saveToken(token: string | null): void {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    /* Storage may be disabled; the current in-memory session still works. */
  }
}

export function readToken(): string | null {
  try {
    const token = sessionStorage.getItem(TOKEN_KEY);
    if (token && (tokenExpiry(token) || 0) > Date.now()) return token;
    saveToken(null);
  } catch {
    /* No persisted session is available. */
  }
  return null;
}
