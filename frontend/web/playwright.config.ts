import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
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
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
