import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60000,
  reporter: "list",
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:5175",
    viewport: { width: 1440, height: 1100 },
    trace: "off",
    screenshot: "only-on-failure",
  },
});
