import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/prod-smoke",
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  outputDir: "test-results/prod-smoke",
  use: {
    baseURL: process.env.GUIDED_OPERATIONS_SMOKE_BASE_URL
      ?? "http://127.0.0.1:8080",
    ...devices["Desktop Chrome"],
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
});
