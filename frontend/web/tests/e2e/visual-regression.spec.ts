import { expect, test, type Locator, type Page } from "@playwright/test";
import { installAdminApi } from "./support/admin-mock-api";
import { installOfficerApi, type OfficerApiState } from "./support/mock-api";

test.beforeEach(() => {
  test.skip(
    process.platform !== "win32",
    "The committed visual baselines target Chromium on Windows; CI verifies them on windows-latest.",
  );
});

const HOME_VIEWPORTS = [
  { name: "1536x1024", width: 1536, height: 1024 },
  { name: "1366x768", width: 1366, height: 768 },
  { name: "1280x800", width: 1280, height: 800 },
  { name: "tablet-portrait", width: 768, height: 1024 },
  { name: "tablet-landscape", width: 1024, height: 768 },
  { name: "mobile-390x844", width: 390, height: 844 },
  { name: "mobile-360x800", width: 360, height: 800 },
  { name: "mobile-430x932", width: 430, height: 932 },
  { name: "mobile-320x568", width: 320, height: 568 },
  { name: "mobile-landscape", width: 844, height: 390 },
] as const;

const OFFICER_ROUTES = [
  { name: "new-report", path: "./new-report", heading: "New Report" },
  { name: "reports", path: "./reports", heading: "Reports" },
  { name: "document-studio", path: "./reports/00000000-0000-4000-8000-000000000010", heading: "Fictional Training Incident" },
  { name: "policy-expert", path: "./policy-expert", heading: "Policy Expert" },
  { name: "forms-library", path: "./forms", heading: "Forms Library" },
  { name: "account", path: "./account", heading: "My Account" },
  { name: "count-sheet", path: "./count-sheet", heading: "NCU Days Count" },
] as const;

const ADMIN_ROUTES = [
  { name: "overview", path: "./admin/overview", heading: "Operational Command Center" },
  { name: "all-incidents", path: "./admin/incidents", heading: "All Incidents" },
  { name: "paperwork", path: "./admin/paperwork?tab=daily&work_date=2026-08-20&shift=D", heading: "Paperwork Center" },
  { name: "accounts-staff", path: "./admin/accounts-staff", heading: "Accounts & Staff" },
  { name: "audit", path: "./admin/audit", heading: "Audit Log" },
  { name: "health", path: "./admin/health", heading: "System Health" },
  { name: "review-lab", path: "./admin/review-lab", heading: "Review Lab" },
] as const;

function dynamicMasks(page: Page): Locator[] {
  return [
    page.locator("time"),
    page.locator(".officer-home-form-updated"),
    page.locator(".gow-online-dot"),
  ];
}

async function expectViewportScreenshot(page: Page, name: string): Promise<void> {
  await expect(page).toHaveScreenshot(`${name}.png`, {
    animations: "disabled",
    caret: "hide",
    fullPage: false,
    mask: dynamicMasks(page),
    maxDiffPixelRatio: 0.01,
  });
}

async function expectWorkspaceScreenshot(page: Page, name: string): Promise<void> {
  await expect(page.locator("main.gow-workspace")).toHaveScreenshot(`${name}.png`, {
    animations: "disabled",
    caret: "hide",
    mask: dynamicMasks(page),
    maxDiffPixelRatio: 0.01,
  });
}

async function expectPrintScreenshot(locator: Locator, name: string): Promise<void> {
  await expect(locator).toHaveScreenshot(`${name}.png`, {
    animations: "disabled",
    caret: "hide",
    maxDiffPixelRatio: 0.01,
  });
}

async function enterAdmin(page: Page): Promise<void> {
  await page.goto("./admin/overview");
  await page.getByLabel("Administrator PIN").fill("A12345");
  await page.getByRole("button", { name: "Enter Admin Center" }).click();
  await expect(page.getByRole("navigation", { name: "Administration navigation" })).toBeVisible();
}

test.describe("Home visual regression", () => {
  let officerApiState: OfficerApiState;
  test.beforeEach(async ({ page }) => { officerApiState = await installOfficerApi(page); });

  for (const viewport of HOME_VIEWPORTS) {
    test(`Home matches the ${viewport.name} baseline`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await page.goto("./");
      await expect(page.getByRole("heading", { name: "Officer Casey Morgan", level: 1 })).toBeVisible();
      await expectViewportScreenshot(page, `home-${viewport.name}`);
    });
  }

  test("mobile drawer open matches its baseline", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("./");
    await page.getByRole("button", { name: "Open navigation menu" }).click();
    await expect(page.getByRole("navigation", { name: "Officer navigation" })).toBeVisible();
    await expectViewportScreenshot(page, "home-mobile-drawer-open");
  });

  test("profile menu open matches its baseline", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto("./");
    await page.getByRole("button", { name: "Officer Casey Morgan" }).click();
    await expect(page.getByRole("menu", { name: "Profile and session" })).toBeVisible();
    await expectViewportScreenshot(page, "home-profile-menu-open");
  });

  test("keyboard focus matches its baseline", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto("./");
    await page.getByRole("region", { name: "Primary actions" })
      .getByRole("link", { name: "New Incident Report" })
      .focus();
    await expectViewportScreenshot(page, "home-keyboard-focus");
  });

  test("recoverable Home error matches its baseline", async ({ page }) => {
    officerApiState.homeFailuresRemaining = 2;
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto("./");
    await expect(page.getByRole("alert")).toBeVisible();
    await expectViewportScreenshot(page, "home-recoverable-error");
  });

  test("Home loading state matches its baseline", async ({ page }) => {
    officerApiState.homeDelayMs = 10_000;
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto("./");
    await expect(page.locator(".officer-home-state[aria-busy='true']")).toBeVisible();
    await expectViewportScreenshot(page, "home-loading");
  });

  test("Home authorized empty state matches its baseline", async ({ page }) => {
    officerApiState.homeEmpty = true;
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto("./");
    await expect(page.getByText("No unfinished incidents")).toBeVisible();
    await expect(page.getByText("No recent incidents are available.")).toBeVisible();
    await expect(page.getByText("No approved quick forms are available.")).toBeVisible();
    await expectViewportScreenshot(page, "home-authorized-empty");
  });

  test("browser-offline topbar matches its honest connectivity baseline", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto("./");
    await page.context().setOffline(true);
    await expect(page.getByRole("status").filter({ hasText: "Offline" })).toBeVisible();
    await expectViewportScreenshot(page, "home-browser-offline");
  });

  test("reduced-motion Home matches its baseline", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto("./");
    await expect(page.getByRole("region", { name: "Primary actions" })).toBeVisible();
    await expectViewportScreenshot(page, "home-reduced-motion");
  });
});

test.describe("representative route visual regression", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await installOfficerApi(page);
  });

  for (const route of OFFICER_ROUTES) {
    test(`${route.heading} matches its officer-route baseline`, async ({ page }) => {
      await page.goto(route.path);
      await expect(page.getByRole("heading", { name: route.heading, level: 1, exact: true })).toBeVisible();
      if (route.name === "reports") {
        await expect(page.getByText("2026-08-029", { exact: true })).toBeVisible();
        await expect(page.getByText("Fictional Training Incident", { exact: true })).toBeVisible();
        await expect(page.getByRole("alert")).toHaveCount(0);
      }
      await expectWorkspaceScreenshot(page, `officer-${route.name}`);
    });
  }
});

test.describe("primary officer mobile visual regression", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await installOfficerApi(page);
  });

  for (const route of OFFICER_ROUTES) {
    test(`${route.heading} matches its mobile officer-route baseline`, async ({ page }) => {
      await page.goto(route.path);
      await expect(page.getByRole("heading", { name: route.heading, level: 1, exact: true })).toBeVisible();
      if (route.name === "reports") {
        await expect(page.getByText("2026-08-029", { exact: true })).toBeVisible();
        await expect(page.getByText("Fictional Training Incident", { exact: true })).toBeVisible();
        await expect(page.getByRole("alert")).toHaveCount(0);
      }
      await expectViewportScreenshot(page, `officer-mobile-${route.name}`);
    });
  }
});

test.describe("representative administrator visual regression", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await installAdminApi(page);
  });

  for (const route of ADMIN_ROUTES) {
    test(`${route.heading} matches its administrator baseline`, async ({ page }) => {
      await enterAdmin(page);
      await page.goto(route.path);
      await expect(page.getByRole("heading", { name: route.heading, level: 1, exact: true })).toBeVisible();
      await expectWorkspaceScreenshot(page, `admin-${route.name}`);
    });
  }
});

test.describe("administrator mobile navigation visual regression", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await installAdminApi(page);
  });

  test("administrator navigation matches its mobile baseline", async ({ page }) => {
    await enterAdmin(page);
    await expect(page.getByRole("navigation", { name: "Administration navigation" })).toBeVisible();
    await expectViewportScreenshot(page, "admin-mobile-navigation");
  });
});

test.describe("paperwork print visual regression", () => {
  test("NCU Days Count matches its print baseline", async ({ page }) => {
    await installOfficerApi(page);
    await page.goto("./count-sheet");
    await page.getByLabel("Date", { exact: true }).fill("2026-08-20");
    await page.getByRole("button", { name: "Preview Print Layout", exact: true }).click();
    await page.emulateMedia({ media: "print" });
    const print = page.getByLabel("Count Sheet print preview", { exact: true }).last();
    await expect(print).toBeVisible();
    await expectPrintScreenshot(print, "print-count-sheet");
  });

  for (const template of [
    { button: "Preview Windows, Bars & Doors Check", name: "windows-bars-doors" },
    { button: "Preview Chemical Agents", name: "chemical-agents" },
    { button: "Preview Contraband Search — Standard Area Rotation", name: "contraband-standard" },
    { button: "Preview Contraband Search — Expanded Area Rotation", name: "contraband-expanded" },
  ] as const) {
    test(`${template.name} matches its monthly print baseline`, async ({ page }) => {
      await installAdminApi(page);
      await enterAdmin(page);
      await page.goto("./admin/paperwork?tab=monthly");
      await expect(page.getByRole("heading", { name: "Paperwork Center", level: 1 })).toBeVisible();
      await expect(page.getByRole("tab", { name: "Monthly" })).toHaveAttribute("aria-selected", "true");
      await page.getByLabel("Month", { exact: true }).fill("2026-08");
      await page.getByLabel("Shift", { exact: true }).fill("D");
      await page.getByRole("button", { name: template.button, exact: true }).click();
      await page.emulateMedia({ media: "print" });
      const print = page.locator(".print-document");
      await expect(print).toHaveCount(1);
      await expectPrintScreenshot(print, `print-monthly-${template.name}`);
    });
  }

  test("incident-specific digital form matches its print baseline with unknowns visible", async ({ page }) => {
    const officerApiState = await installOfficerApi(page);
    officerApiState.showIncidentPaperwork = true;
    await page.goto("./reports/00000000-0000-4000-8000-000000000010");
    await page.getByRole("tab", { name: "Required Paperwork" }).click();
    await page.getByRole("button", { name: "Preview Medical Documentation Checklist" }).click();
    const preview = page.locator(".iw-form-preview");
    await expect(preview).toContainText("Missing Information");
    await expect(preview).toContainText("Medical Provider");
    await page.emulateMedia({ media: "print" });
    await expectPrintScreenshot(preview, "print-incident-medical-checklist");
  });
});

test.describe("Windows display scaling visual regression at 125 percent", () => {
  test.use({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1.25 });
  test.beforeEach(async ({ page }) => { await installOfficerApi(page); });

  test("Home matches the 125 percent device-scale baseline", async ({ page }) => {
    await page.goto("./");
    await expect(page.getByRole("heading", { name: "Officer Casey Morgan", level: 1 })).toBeVisible();
    await expectViewportScreenshot(page, "home-windows-scale-125");
  });
});

test.describe("Windows display scaling visual regression at 150 percent", () => {
  test.use({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1.5 });
  test.beforeEach(async ({ page }) => { await installOfficerApi(page); });

  test("Home matches the 150 percent device-scale baseline", async ({ page }) => {
    await page.goto("./");
    await expect(page.getByRole("heading", { name: "Officer Casey Morgan", level: 1 })).toBeVisible();
    await expectViewportScreenshot(page, "home-windows-scale-150");
  });
});
