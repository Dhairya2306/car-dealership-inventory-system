import { test, expect, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";

const password = `Browser-test-${randomUUID()}`;
const screenshotDir = "../docs/screenshots";

// These two journeys share inventory in the runner's disposable database.
test.describe.configure({ mode: "serial" });

async function login(page: Page, email: string, secret: string) {
  await page.goto("/login");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(secret);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Vehicle inventory", exact: true }),
  ).toBeVisible();
}

test("real user registration, CRUD, search, pagination, purchases, refresh and logout", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const email = `browser-${randomUUID()}@example.com`;
  await page.goto("/inventory");
  await expect(page).toHaveURL(/\/login$/);
  await page.screenshot({ path: `${screenshotDir}/login.png`, fullPage: true });
  await page.getByRole("link", { name: "Create an account" }).click();
  await page.screenshot({
    path: `${screenshotDir}/registration.png`,
    fullPage: true,
  });
  await page.getByLabel("Name", { exact: true }).fill("Alex Morgan");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Vehicle inventory", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Add vehicle", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Make", { exact: true }).fill("Honda");
  await dialog.getByLabel("Model", { exact: true }).fill("City");
  await dialog.getByLabel("Category", { exact: true }).fill("Sedan");
  await dialog.getByLabel("Price", { exact: true }).fill("1450000.25");
  await dialog.getByLabel("Initial stock").fill("2");
  await dialog
    .getByRole("button", { name: "Add vehicle", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Honda City", exact: true }),
  ).toBeVisible();

  const token = await page.evaluate(() =>
    sessionStorage.getItem("dealership.access-token"),
  );
  const samples = [
    ["Toyota", "Fortuner", "SUV", "3500000", 6],
    ["Hyundai", "Creta", "SUV", "1600000", 3],
    ["Maruti Suzuki", "Swift", "Hatchback", "850000", 8],
    ["Tata", "Nexon", "SUV", "1350000", 0],
    ["Mahindra", "XUV700", "SUV", "2200000", 4],
    ["Kia", "Seltos", "SUV", "1700000", 5],
    ["Toyota", "Camry", "Sedan", "4500000", 2],
    ["Volkswagen", "Virtus", "Sedan", "1800000", 4],
    ["Skoda", "Slavia", "Sedan", "1750000", 1],
    ["Hyundai", "i20", "Hatchback", "1100000", 7],
    ["Tata", "Tiago", "Hatchback", "750000", 5],
    ["Mahindra", "Thar", "SUV", "1900000", 3],
  ];
  for (const [make, model, category, price, quantity] of samples) {
    const response = await page.request.post("/api/vehicles", {
      headers: { Authorization: `Bearer ${token}` },
      data: { make, model, category, price, quantity },
    });
    expect(response.status()).toBe(201);
  }
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.getByText("Page 1 of 2")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Purchase Tata Nexon" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Dismiss notification" }).click();
  await page.screenshot({
    path: `${screenshotDir}/inventory-desktop.png`,
    fullPage: true,
  });
  await page.getByRole("button", { name: "Next page" }).click();
  await expect(page.getByText("Page 2 of 2")).toBeVisible();
  await page.getByRole("button", { name: "Previous page" }).click();
  await expect(page.getByText("Page 1 of 2")).toBeVisible();
  await page.getByLabel("Make", { exact: true }).fill("Honda");
  await page.getByLabel("Minimum price").fill("1000000");
  await page.getByRole("button", { name: "Search inventory" }).click();
  await expect(page.getByText("Showing 1–1 of 1 vehicles")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Delete Honda City" }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Edit Honda City" }).click();
  await dialog.getByLabel("Model", { exact: true }).fill("City Hybrid");
  await dialog.getByRole("button", { name: "Save changes" }).click();
  await expect(
    page.getByRole("heading", { name: "Honda City Hybrid" }),
  ).toBeVisible();
  for (let index = 0; index < 2; index++) {
    await page
      .getByRole("button", { name: "Purchase Honda City Hybrid" })
      .click();
    await expect(
      page.getByText(index === 0 ? "1 available" : "Out of stock", {
        exact: true,
      }),
    ).toBeVisible();
  }
  await expect(
    page.getByRole("button", { name: "Purchase Honda City Hybrid" }),
  ).toBeDisabled();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Vehicle inventory", exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("heading", { name: "Honda City Hybrid" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: `${screenshotDir}/inventory-mobile.png`,
    fullPage: true,
  });
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await login(page, email, password);
  await page.evaluate(() =>
    sessionStorage.setItem("dealership.access-token", "invalid"),
  );
  await page.reload();
  await expect(page).toHaveURL(/\/login$/);
  expect(errors).toEqual([]);
});

test("real admin restock, deletion confirmation and keyboard dialog dismissal", async ({
  page,
}) => {
  await login(
    page,
    process.env.E2E_ADMIN_EMAIL!,
    process.env.E2E_ADMIN_PASSWORD!,
  );
  await page.getByLabel("Make", { exact: true }).fill("Honda");
  await page.getByRole("button", { name: "Search inventory" }).click();
  await expect(page.getByText("Showing 1–1 of 1 vehicles")).toBeVisible();
  await page.getByRole("button", { name: "Restock Honda City Hybrid" }).click();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("button", { name: "Restock Honda City Hybrid" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Units to add").fill("3");
  await dialog.getByRole("button", { name: "Add stock", exact: true }).click();
  await expect(page.getByText("3 available")).toBeVisible();
  await page.getByRole("button", { name: "Delete Honda City Hybrid" }).click();
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(
    page.getByRole("heading", { name: "Honda City Hybrid" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Delete Honda City Hybrid" }).click();
  await dialog
    .getByRole("button", { name: "Delete vehicle", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "No vehicles match your filters" }),
  ).toBeVisible();
});
