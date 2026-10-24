import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import {
  car,
  inventory,
  json,
  mockApi,
  profile,
  renderApp,
} from "../test/helpers";

it("renders inventory and disables zero-stock purchase; hides admin actions from users", async () => {
  mockApi((url) =>
    url.includes("/vehicles?")
      ? json(
          inventory([
            car,
            { ...car, id: "empty", make: "Honda", model: "Civic", quantity: 0 },
          ]),
        )
      : undefined,
  );
  renderApp();
  await screen.findByRole("heading", { name: "Toyota Corolla" });
  expect(
    within(screen.getByRole("listitem", { name: "Toyota Corolla" })).getByText(
      /24,500.25/,
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Purchase Honda Civic" }),
  ).toBeDisabled();
  expect(
    screen.queryByRole("button", { name: "Delete Toyota Corolla" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Restock Toyota Corolla" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Edit Toyota Corolla" }),
  ).toBeEnabled();
});
it("applies combined filters and rejects inverted prices", async () => {
  const user = userEvent.setup();
  const fetcher = mockApi();
  renderApp();
  await screen.findByText("Toyota Corolla");
  await user.type(screen.getByLabelText("Make"), "Toyota");
  await user.type(screen.getByLabelText("Category"), "Sedan");
  await user.type(screen.getByLabelText("Minimum price"), "500");
  await user.type(screen.getByLabelText("Maximum price"), "100");
  await user.click(screen.getByRole("button", { name: "Search inventory" }));
  expect(screen.getByRole("alert")).toHaveTextContent("must not exceed");
  await user.clear(screen.getByLabelText("Maximum price"));
  await user.type(screen.getByLabelText("Maximum price"), "30000");
  await user.click(screen.getByRole("button", { name: "Search inventory" }));
  await waitFor(() =>
    expect(
      fetcher.mock.calls.some(
        ([url]) =>
          url.includes("/vehicles/search?") &&
          url.includes("make=Toyota") &&
          url.includes("category=Sedan") &&
          url.includes("max_price=30000"),
      ),
    ).toBe(true),
  );
});
it("paginates with backend offset and returns to the first page", async () => {
  const user = userEvent.setup();
  const fetcher = mockApi((url) =>
    url.includes("/vehicles?")
      ? json(inventory([car], 11, url.includes("offset=10") ? 10 : 0))
      : undefined,
  );
  renderApp();
  await screen.findByText("Toyota Corolla");
  await user.click(screen.getByRole("button", { name: "Next page" }));
  await screen.findByText("Page 2 of 2");
  expect(fetcher.mock.calls.some(([url]) => url.includes("offset=10"))).toBe(
    true,
  );
  await user.click(screen.getByRole("button", { name: "Previous page" }));
  await screen.findByText("Page 1 of 2");
});
it("purchases exactly one unit and refreshes inventory", async () => {
  let quantity = 2;
  const user = userEvent.setup();
  const fetcher = mockApi((url) => {
    if (url.endsWith("/purchase")) {
      quantity--;
      return json({ ...car, quantity });
    }
    if (url.includes("/vehicles?"))
      return json(inventory([{ ...car, quantity }]));
  });
  renderApp();
  await screen.findByText("Toyota Corolla");
  await user.click(
    screen.getByRole("button", { name: "Purchase Toyota Corolla" }),
  );
  await screen.findByText("1 available");
  expect(screen.getByRole("status")).toHaveTextContent(
    "Purchased one Toyota Corolla",
  );
  const request = fetcher.mock.calls.find(([url]) => url.endsWith("/purchase"));
  expect(request![1]!.body).toBeUndefined();
});
it("reports concurrent stock conflicts and refreshes without going negative", async () => {
  const user = userEvent.setup();
  mockApi((url) =>
    url.endsWith("/purchase")
      ? json({ detail: "Vehicle is out of stock" }, 409)
      : undefined,
  );
  renderApp();
  await screen.findByText("Toyota Corolla");
  await user.click(
    screen.getByRole("button", { name: "Purchase Toyota Corolla" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Vehicle is out of stock",
  );
});
it("renders loading, then an empty inventory", async () => {
  let resolve!: (response: Response) => void;
  mockApi((url) =>
    url.includes("/vehicles?")
      ? new Promise<Response>((done) => {
          resolve = done;
        })
      : undefined,
  );
  renderApp();
  await screen.findByText("Loading inventory…");
  resolve(json(inventory([])));
  await screen.findByText("Your inventory starts here");
});
it("shows API errors and retries inventory loading", async () => {
  let broken = true;
  const user = userEvent.setup();
  mockApi((url) =>
    url.includes("/vehicles?") && broken
      ? json({ detail: "Service unavailable" }, 503)
      : undefined,
  );
  renderApp();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Service unavailable",
  );
  broken = false;
  await user.click(screen.getByRole("button", { name: "Try again" }));
  await screen.findByText("Toyota Corolla");
});
it("validates create input and sends a decimal string with integer quantity", async () => {
  const user = userEvent.setup();
  const fetcher = mockApi((url) =>
    url === "/api/vehicles" ? json(car, 201) : undefined,
  );
  renderApp();
  await screen.findByText("Toyota Corolla");
  await user.click(screen.getByRole("button", { name: "Add vehicle" }));
  const dialog = within(screen.getByRole("dialog"));
  await user.click(dialog.getByRole("button", { name: "Add vehicle" }));
  expect(dialog.getByRole("alert")).toHaveTextContent("required");
  for (const [label, value] of [
    ["Make", "Honda"],
    ["Model", "Civic"],
    ["Category", "Sedan"],
    ["Price", "100.25"],
  ])
    await user.type(dialog.getByLabelText(label), value);
  await user.click(dialog.getByRole("button", { name: "Add vehicle" }));
  await waitFor(() =>
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
  );
  const request = fetcher.mock.calls.find(([url]) => url === "/api/vehicles");
  expect(JSON.parse(request![1]!.body as string)).toEqual({
    make: "Honda",
    model: "Civic",
    category: "Sedan",
    price: "100.25",
    quantity: 0,
  });
});
it("updates details without sending stock", async () => {
  const user = userEvent.setup();
  const fetcher = mockApi((url) =>
    url === "/api/vehicles/vehicle-1" ? json(car) : undefined,
  );
  renderApp();
  await screen.findByText("Toyota Corolla");
  await user.click(screen.getByRole("button", { name: "Edit Toyota Corolla" }));
  const dialog = within(screen.getByRole("dialog"));
  await user.click(dialog.getByRole("button", { name: "Save changes" }));
  await waitFor(() =>
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
  );
  const request = fetcher.mock.calls.find(
    ([url]) => url === "/api/vehicles/vehicle-1",
  );
  expect(JSON.parse(request![1]!.body as string)).not.toHaveProperty(
    "quantity",
  );
});
it("shows admin actions, validates restock and confirms deletion", async () => {
  const user = userEvent.setup();
  const fetcher = mockApi(
    (url, init) => {
      if (init?.method === "DELETE") return json(null, 204);
      if (url.endsWith("/restock")) return json({ ...car, quantity: 5 });
    },
    { ...profile, role: "admin" },
  );
  renderApp();
  await screen.findByText("Toyota Corolla");
  await user.click(
    screen.getByRole("button", { name: "Restock Toyota Corolla" }),
  );
  let dialog = within(screen.getByRole("dialog"));
  await user.clear(dialog.getByLabelText("Units to add"));
  await user.type(dialog.getByLabelText("Units to add"), "0");
  await user.click(dialog.getByRole("button", { name: "Add stock" }));
  expect(dialog.getByRole("alert")).toHaveTextContent("positive");
  await user.clear(dialog.getByLabelText("Units to add"));
  await user.type(dialog.getByLabelText("Units to add"), "3");
  await user.click(dialog.getByRole("button", { name: "Add stock" }));
  await waitFor(() =>
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
  );
  await screen.findByText("Toyota Corolla");
  await user.click(
    screen.getByRole("button", { name: "Delete Toyota Corolla" }),
  );
  dialog = within(screen.getByRole("dialog"));
  expect(dialog.getByText(/cannot be undone/)).toBeInTheDocument();
  expect(fetcher.mock.calls.some(([, init]) => init?.method === "DELETE")).toBe(
    false,
  );
  await user.click(dialog.getByRole("button", { name: "Delete vehicle" }));
  await waitFor(() =>
    expect(
      fetcher.mock.calls.some(([, init]) => init?.method === "DELETE"),
    ).toBe(true),
  );
});
