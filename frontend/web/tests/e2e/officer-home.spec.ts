import { expect, test } from "@playwright/test";
import { installOfficerApi } from "./support/mock-api";

const HOME_VIEWPORTS = [
  { name: "wide desktop", width: 1536, height: 1024 },
  { name: "standard desktop", width: 1366, height: 768 },
  { name: "short laptop", width: 1280, height: 720 },
  { name: "tablet portrait", width: 768, height: 1024 },
  { name: "tablet landscape", width: 1024, height: 768 },
  { name: "large mobile", width: 430, height: 932 },
  { name: "mobile", width: 390, height: 844 },
  { name: "small mobile", width: 360, height: 800 },
  { name: "minimum mobile", width: 320, height: 568 },
  { name: "mobile landscape", width: 844, height: 390 },
] as const;

const PRIMARY_ACTION_NAMES = [
  "New Incident Report",
  "Open Count Sheet",
  "Ask a Policy Question",
  "Open Forms Library",
] as const;

test.beforeEach(async ({ page }) => {
  await installOfficerApi(page);
});

test("officer Home uses authenticated work and keeps the incident action dominant", async ({ page }) => {
  await page.goto("./");

  await expect(page.getByRole("heading", { name: "Officer Casey Morgan" })).toBeVisible();
  await expect(page.getByText("Fictional Training Incident").first()).toBeVisible();
  await expect(page.getByText("2026-08-029").first()).toBeVisible();
  await expect(page.getByText("Barracks 4 Fight")).toHaveCount(0);

  const actions = page.getByRole("region", { name: "Primary actions" });
  const start = actions.getByRole("link", { name: "New Incident Report" });
  await expect(start).toHaveClass(/primary/);
  await expect(actions.getByRole("link", { name: "Open Count Sheet" })).toBeVisible();
  await expect(actions.getByRole("link", { name: "Ask a Policy Question" })).toBeVisible();
  await expect(actions.getByRole("link", { name: "Open Forms Library" })).toBeVisible();
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

  const actions = page.getByRole("region", { name: "Primary actions" });
  await expect(actions.getByRole("link", { name: "New Incident Report" })).toBeVisible();
  await actions.getByRole("link", { name: "Open Forms Library" }).focus();
  await expect(actions.getByRole("link", { name: "Open Forms Library" })).toBeFocused();
});

test("major Home actions meet the minimum touch-target size", async ({ page }) => {
  await page.goto("./");

  const actions = page.getByRole("region", { name: "Primary actions" });
  for (const name of PRIMARY_ACTION_NAMES) {
    const box = await actions.getByRole("link", { name, exact: true }).boundingBox();
    expect(box, `${name} must have a measurable box`).not.toBeNull();
    expect(box!.width, `${name} must be at least 44 CSS pixels wide`).toBeGreaterThanOrEqual(44);
    expect(box!.height, `${name} must be at least 44 CSS pixels tall`).toBeGreaterThanOrEqual(44);
  }
});

test("the 768px-tall desktop sidebar keeps every primary destination reachable", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("./");

  const navigation = page.getByRole("navigation", { name: "Officer navigation" });
  for (const name of ["Home", "New Report", "Reports", "Policy Expert", "Forms Library", "Account"]) {
    const link = navigation.getByRole("link", { name, exact: true });
    await expect(link).toBeVisible();
    const box = await link.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.y).toBeGreaterThanOrEqual(0);
    expect(box!.y + box!.height).toBeLessThanOrEqual(768);
  }
});

for (const viewport of HOME_VIEWPORTS) {
  test(`Home reflows without horizontal page overflow at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("./");

    await expect(page.getByRole("heading", { name: "Officer Casey Morgan" })).toBeVisible();
    const actions = page.getByRole("region", { name: "Primary actions" });
    for (const name of PRIMARY_ACTION_NAMES) {
      await expect(actions.getByRole("link", { name, exact: true })).toBeVisible();
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 2)).toBe(true);
  });
}

for (const zoom of [80, 100, 125, 150] as const) {
  test(`Home preserves its primary controls at ${zoom} percent browser-zoom equivalent`, async ({ page }) => {
    const scale = zoom / 100;
    await page.setViewportSize({
      width: Math.floor(1366 / scale),
      height: Math.floor(768 / scale),
    });
    await page.goto("./");

    const actions = page.getByRole("region", { name: "Primary actions" });
    for (const name of PRIMARY_ACTION_NAMES) {
      await expect(actions.getByRole("link", { name, exact: true })).toBeVisible();
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 2)).toBe(true);
  });
}

test("Home supports 200 percent text sizing without horizontal page overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("./");
  await page.evaluate(() => { document.documentElement.style.fontSize = "200%"; });

  await expect(page.getByRole("heading", { name: "Officer Casey Morgan" })).toBeVisible();
  const actions = page.getByRole("region", { name: "Primary actions" });
  for (const name of PRIMARY_ACTION_NAMES) {
    await expect(actions.getByRole("link", { name, exact: true })).toBeVisible();
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 2)).toBe(true);
});

test("Home reflows at 400 percent text sizing without losing primary controls", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 568 });
  await page.goto("./");
  await page.evaluate(() => { document.documentElement.style.fontSize = "400%"; });

  await expect(page.getByRole("heading", { name: "Officer Casey Morgan" })).toBeVisible();
  const actions = page.getByRole("region", { name: "Primary actions" });
  for (const name of PRIMARY_ACTION_NAMES) {
    await expect(actions.getByRole("link", { name, exact: true })).toBeVisible();
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 2)).toBe(true);
});

test("forced-colors mode preserves current-page and keyboard-focus semantics", async ({ page }) => {
  await page.emulateMedia({ forcedColors: "active" });
  await page.goto("./");

  const home = page.getByRole("navigation", { name: "Officer navigation" }).getByRole("link", { name: "Home" });
  await expect(home).toHaveAttribute("aria-current", "page");

  const action = page.getByRole("region", { name: "Primary actions" }).getByRole("link", { name: "New Incident Report" });
  await action.focus();
  await expect(action).toBeFocused();
  expect(await action.evaluate((element) => {
    const style = getComputedStyle(element);
    return style.outlineStyle !== "none" || style.boxShadow !== "none";
  })).toBe(true);
});

test("Home decorative scenery is excluded from print", async ({ page }) => {
  await page.goto("./");
  await page.emulateMedia({ media: "print" });

  await expect(page.locator(".gow-sidebar-mountain-scene")).toBeHidden();
  await expect(page.locator(".officer-home-hero")).toHaveCSS("background-image", "none");
});

test("Home remains fully operable when decorative images fail", async ({ page }) => {
  await page.route("**/*.webp", (route) => route.abort("failed"));
  await page.goto("./");

  await expect(page.getByRole("heading", { name: "Officer Casey Morgan" })).toBeVisible();
  const actions = page.getByRole("region", { name: "Primary actions" });
  for (const name of PRIMARY_ACTION_NAMES) {
    await expect(actions.getByRole("link", { name, exact: true })).toBeVisible();
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 2)).toBe(true);
});

test("fixed scenic geometry avoids measurable layout shift during Home load", async ({ page }) => {
  await page.addInitScript(() => {
    (window as Window & { __gowLayoutShift?: number }).__gowLayoutShift = 0;
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const shift = entry as PerformanceEntry & { hadRecentInput?: boolean; value?: number };
        if (!shift.hadRecentInput) {
          (window as Window & { __gowLayoutShift?: number }).__gowLayoutShift! += shift.value ?? 0;
        }
      }
    }).observe({ type: "layout-shift", buffered: true });
  });
  await page.goto("./");
  await expect(page.getByRole("heading", { name: "Officer Casey Morgan" })).toBeVisible();
  await page.waitForLoadState("networkidle");

  const layoutShift = await page.evaluate(() => (window as Window & { __gowLayoutShift?: number }).__gowLayoutShift ?? 0);
  expect(layoutShift).toBeLessThanOrEqual(0.1);
});
