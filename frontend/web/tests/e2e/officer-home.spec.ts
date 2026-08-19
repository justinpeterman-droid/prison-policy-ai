import { expect, test } from "@playwright/test";
import { installOfficerApi } from "./support/mock-api";

test.beforeEach(async ({ page }) => {
  await installOfficerApi(page);
});

test("officer Home uses authenticated work and keeps the incident action dominant", async ({ page }) => {
  await page.goto("./");

  await expect(page.getByRole("heading", { name: "Officer Casey Morgan" })).toBeVisible();
  await expect(page.getByText("Fictional Training Incident").first()).toBeVisible();
  await expect(page.getByText("2026-08-029").first()).toBeVisible();
  await expect(page.getByText("Barracks 4 Fight")).toHaveCount(0);

  const start = page.getByRole("link", { name: "Start New Incident" });
  await expect(start).toHaveClass(/primary/);
  await expect(page.getByRole("link", { name: "Open Count Sheet" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Ask a Policy Question" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Open Forms Library" })).toBeVisible();
  await expect(page.getByText("Secure browser session")).toBeVisible();
  await expect(page.getByText(/Last synced 2 minutes ago/i)).toHaveCount(0);
});

test("mobile officer navigation opens without hiding the active workspace", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("./");

  await expect(page.getByRole("heading", { name: "Officer Casey Morgan" })).toBeVisible();
  await page.getByRole("button", { name: "Open navigation menu" }).click();
  const navigation = page.getByRole("navigation", { name: "Officer navigation" });
  await expect(navigation.getByRole("link", { name: "Policy Expert" })).toBeVisible();
  await navigation.getByRole("link", { name: "Forms Library" }).click();

  await expect(page.getByRole("heading", { name: "Forms Library" })).toBeVisible();
  await expect(page.getByText("PHYSICAL CARBON-COPY FORM REQUIRED")).toBeVisible();
});

test("officer Home remains usable with reduced motion enabled", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("./");

  await expect(page.getByRole("link", { name: "Start New Incident" })).toBeVisible();
  await page.getByRole("link", { name: "Open Forms Library" }).focus();
  await expect(page.getByRole("link", { name: "Open Forms Library" })).toBeFocused();
});
