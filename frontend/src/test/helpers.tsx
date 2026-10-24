import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import App from "../App";
import { AuthProvider } from "../auth/AuthProvider";
import { TOKEN_KEY } from "../lib/session";
import type { User, Vehicle } from "../lib/types";

export const profile: User = {
  id: "user-1",
  email: "alex@example.com",
  name: "Alex Morgan",
  role: "user",
  created_at: "",
  updated_at: "",
};
export const car: Vehicle = {
  id: "vehicle-1",
  make: "Toyota",
  model: "Corolla",
  category: "Sedan",
  price: "24500.25",
  quantity: 2,
  created_at: "",
  updated_at: "",
};
export function testToken(exp = Date.now() / 1000 + 3600) {
  return `test.${btoa(JSON.stringify({ exp }))}.test-signature`;
}
export function json(data: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
export function inventory(items = [car], total = items.length, offset = 0) {
  return { items, total, offset, limit: 10 };
}
export function mockApi(
  handler?: (
    url: string,
    init?: RequestInit,
  ) => Response | Promise<Response> | undefined,
  user = profile,
) {
  const fetcher = vi.fn(async (url: string, init?: RequestInit) => {
    const custom = handler?.(String(url), init);
    if (custom) return custom;
    if (url.endsWith("/auth/me")) return json(user);
    if (url.endsWith("/auth/login"))
      return json({
        access_token: testToken(),
        token_type: "bearer",
        expires_in: 3600,
      });
    if (url.endsWith("/auth/register")) return json(user, 201);
    if (url.includes("/vehicles?") || url.includes("/vehicles/search?"))
      return json(inventory());
    throw new Error(`Unexpected request in test: ${url}`);
  });
  vi.stubGlobal("fetch", fetcher);
  return fetcher;
}
export function renderApp(path = "/inventory", authenticated = true) {
  if (authenticated) sessionStorage.setItem(TOKEN_KEY, testToken());
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  );
}
