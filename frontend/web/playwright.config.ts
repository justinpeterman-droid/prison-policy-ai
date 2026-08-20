import { defineConfig, devices } from "@playwright/test";

const visualRegressionFile = /visual-regression\.spec\.ts/;
const skipPlatformSpecificSnapshots = process.env.PLAYWRIGHT_SKIP_VISUAL_REGRESSION === "1";

export default defineConfig({
  testDir: "./tests/e2e",
  // Visual baselines are intentionally captured on the supported Windows
  // workstation platform. Linux CI still runs every behavioral browser test;
  // the dedicated Windows job below the officer-utilities gate owns pixels.
  testIgnore: skipPlatformSpecificSnapshots ? visualRegressionFile : undefined,
  timeout: 30_000,
  expect: { timeout: 8_000 },
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  // Screenshot baselines and the image-failure coverage exercise Chromium's
  // compositor heavily. Keep local runs aligned with CI so concurrent browser
  // contexts cannot produce resource-starved blank frames.
  workers: 1,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: "http://127.0.0.1:4173/workspace/",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    // Production assets are mounted at /static/web, but browser workflows need
    // Vite's SPA fallback at /workspace so BrowserRouter can exercise the real
    // application routes. The CLI base override is test-only.
    command: "npm run dev -- --host 127.0.0.1 --port 4173 --base /",
    url: "http://127.0.0.1:4173/workspace/",
    // A reused local Vite process can be owned by an earlier Playwright run
    // and disappear while a later suite is still using it. Give every run an
    // isolated server lifecycle, matching the dedicated CI jobs.
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
