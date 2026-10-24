import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { json, mockApi, renderApp, testToken } from "../test/helpers";
import { TOKEN_KEY } from "../lib/session";

it("protects inventory when signed out", async () => {
  mockApi();
  renderApp("/inventory", false);
  expect(
    await screen.findByRole("heading", { name: "Welcome back" }),
  ).toBeInTheDocument();
});
it("validates login email and password without calling the API", async () => {
  const user = userEvent.setup();
  const fetcher = mockApi();
  renderApp("/login", false);
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  expect(screen.getByRole("alert")).toHaveTextContent("valid email");
  await user.type(screen.getByLabelText("Email address"), "alex@example.com");
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  expect(screen.getByRole("alert")).toHaveTextContent("Enter your password");
  expect(fetcher).not.toHaveBeenCalled();
});
it("validates registration name and password then submits actual backend fields", async () => {
  const user = userEvent.setup();
  const fetcher = mockApi();
  renderApp("/register", false);
  await user.click(screen.getByRole("button", { name: "Create account" }));
  expect(screen.getByRole("alert")).toHaveTextContent("Enter your name");
  await user.type(screen.getByLabelText("Name"), "Alex Morgan");
  await user.type(screen.getByLabelText("Email address"), "alex@example.com");
  await user.type(screen.getByLabelText("Password"), "short");
  await user.click(screen.getByRole("button", { name: "Create account" }));
  expect(screen.getByRole("alert")).toHaveTextContent("at least 12");
  await user.clear(screen.getByLabelText("Password"));
  await user.type(screen.getByLabelText("Password"), "A long test password!");
  await user.click(screen.getByRole("button", { name: "Create account" }));
  expect(
    await screen.findByRole("heading", { name: "Vehicle inventory" }),
  ).toBeInTheDocument();
  const registration = fetcher.mock.calls.find(([url]) =>
    url.endsWith("/auth/register"),
  );
  expect(JSON.parse(registration![1]!.body as string)).toEqual({
    name: "Alex Morgan",
    email: "alex@example.com",
    password: "A long test password!",
  });
  expect(sessionStorage.getItem(TOKEN_KEY)).not.toBeNull();
});
it("shows login errors without losing form values", async () => {
  const user = userEvent.setup();
  mockApi((url) =>
    url.endsWith("/auth/login")
      ? json({ detail: "Invalid email or password" }, 401)
      : undefined,
  );
  renderApp("/login", false);
  await user.type(screen.getByLabelText("Email address"), "alex@example.com");
  await user.type(screen.getByLabelText("Password"), "wrong password");
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Invalid email or password",
  );
  expect(screen.getByLabelText("Email address")).toHaveValue(
    "alex@example.com",
  );
});
it("restores a saved session through the server and logs out", async () => {
  const user = userEvent.setup();
  const fetcher = mockApi();
  renderApp();
  await screen.findByRole("heading", { name: "Vehicle inventory" });
  expect(fetcher.mock.calls.some(([url]) => url.endsWith("/auth/me"))).toBe(
    true,
  );
  await user.click(screen.getAllByRole("button", { name: "Sign out" })[0]);
  await screen.findByRole("heading", { name: "Welcome back" });
  expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull();
});
it.each(["malformed-token", testToken(Date.now() / 1000 - 100)])(
  "discards invalid/expired saved tokens",
  async (token) => {
    const fetcher = mockApi();
    sessionStorage.setItem(TOKEN_KEY, token);
    renderApp("/inventory", false);
    await screen.findByRole("heading", { name: "Welcome back" });
    expect(fetcher).not.toHaveBeenCalled();
    expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull();
  },
);
it("clears a revoked token rejected by the backend", async () => {
  mockApi((url) =>
    url.endsWith("/auth/me")
      ? json({ detail: "Invalid or expired access token" }, 401)
      : undefined,
  );
  renderApp();
  await screen.findByRole("heading", { name: "Welcome back" });
  expect(sessionStorage.getItem(TOKEN_KEY)).toBeNull();
  expect(screen.getByRole("status")).toHaveTextContent("session expired");
});
it("retains the session on network failure and supports retry", async () => {
  let offline = true;
  const user = userEvent.setup();
  mockApi((url) =>
    url.endsWith("/auth/me") && offline
      ? Promise.reject(new Error("offline"))
      : undefined,
  );
  renderApp();
  await screen.findByRole("heading", {
    name: "Unable to restore your session",
  });
  expect(sessionStorage.getItem(TOKEN_KEY)).not.toBeNull();
  offline = false;
  await user.click(screen.getByRole("button", { name: "Try again" }));
  await waitFor(() =>
    expect(
      screen.getByRole("heading", { name: "Vehicle inventory" }),
    ).toBeInTheDocument(),
  );
});
