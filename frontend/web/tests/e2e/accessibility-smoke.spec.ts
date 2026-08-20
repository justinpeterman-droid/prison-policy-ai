import { expect, test, type Page } from "@playwright/test";
import { installAdminApi } from "./support/admin-mock-api";
import { installOfficerApi, type OfficerApiState } from "./support/mock-api";

const OFFICER_ROUTES = [
  { path: "./", heading: "Officer Casey Morgan", current: "Home" },
  { path: "./new-report", heading: "New Report", current: "New Report" },
  { path: "./reports", heading: "Reports", current: "Reports" },
  { path: "./policy-expert", heading: "Policy Expert", current: "Policy Expert" },
  { path: "./forms", heading: "Forms Library", current: "Forms Library" },
  { path: "./account", heading: "My Account", current: "Account" },
  { path: "./count-sheet", heading: "NCU Days Count" },
] as const;

const ADMIN_ROUTES = [
  { path: "./admin/overview", heading: "Operational Command Center", current: "Overview" },
  { path: "./admin/incidents", heading: "All Incidents", current: "All Incidents" },
  { path: "./admin/paperwork?tab=daily&work_date=2026-08-20&shift=D", heading: "Paperwork Center", current: "Paperwork Center" },
  { path: "./admin/accounts-staff", heading: "Accounts & Staff", current: "Accounts & Staff" },
  { path: "./admin/audit", heading: "Audit Log", current: "Audit Log" },
  { path: "./admin/health", heading: "System Health", current: "System Health" },
  { path: "./admin/review-lab", heading: "Review Lab", current: "Review Lab" },
] as const;

async function expectNamedVisibleControls(page: Page): Promise<void> {
  const unnamed = await page.locator("input, select, textarea").evaluateAll((controls) => controls
    .filter((control) => {
      const element = control as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
      const style = getComputedStyle(element);
      const visible = style.display !== "none" && style.visibility !== "hidden" && element.getClientRects().length > 0;
      if (!visible || (element instanceof HTMLInputElement && element.type === "hidden")) return false;
      return !element.labels?.length
        && !element.getAttribute("aria-label")?.trim()
        && !element.getAttribute("aria-labelledby")?.trim()
        && !element.getAttribute("title")?.trim();
    })
    .map((control) => ({
      tag: control.tagName.toLowerCase(),
      type: control.getAttribute("type"),
      name: control.getAttribute("name"),
      placeholder: control.getAttribute("placeholder"),
    })));
  expect(unnamed, `Visible form controls need programmatic labels: ${JSON.stringify(unnamed)}`).toEqual([]);
}

async function expectPageStructure(page: Page, heading: string): Promise<void> {
  await expect(page.getByRole("heading", { name: heading, level: 1, exact: true })).toBeVisible();
  await expect(page.getByRole("main")).toHaveCount(1);
  await expect(page.getByRole("navigation", { name: "Officer navigation" })).toHaveCount(1);
  await expectNamedVisibleControls(page);
  await expect(page.locator("h1:visible")).toHaveCount(1);
}

async function enterAdmin(page: Page): Promise<void> {
  await page.goto("./admin/overview");
  await page.getByLabel("Administrator PIN").fill("A12345");
  await page.getByRole("button", { name: "Enter Admin Center" }).click();
  await expect(page.getByRole("navigation", { name: "Administration navigation" })).toBeVisible();
}

test.describe("officer route accessibility smoke", () => {
  let officerApiState: OfficerApiState;
  test.beforeEach(async ({ page }) => { officerApiState = await installOfficerApi(page); });

  for (const route of OFFICER_ROUTES) {
    test(`${route.heading} exposes a stable accessible page structure`, async ({ page }) => {
      await page.goto(route.path);
      await expectPageStructure(page, route.heading);
      if ("current" in route) {
        await expect(page.getByRole("navigation", { name: "Officer navigation" })
          .getByRole("link", { name: route.current, exact: true }))
          .toHaveAttribute("aria-current", "page");
      }
    });
  }

  test("profile menu is keyboard operable and returns focus on Escape", async ({ page }) => {
    await page.goto("./");
    const trigger = page.getByRole("button", { name: "Officer Casey Morgan" });
    await trigger.focus();
    await trigger.press("ArrowDown");
    const menu = page.getByRole("menu", { name: "Profile and session" });
    await expect(menu).toBeVisible();
    await expect(menu.getByRole("menuitem").first()).toBeFocused();
    await menu.press("Escape");
    await expect(menu).toHaveCount(0);
    await expect(trigger).toBeFocused();
  });

  test("Home load error exposes keyboard-reachable recovery", async ({ page }) => {
    // React StrictMode starts the initial effect twice in the E2E dev server.
    officerApiState.homeFailuresRemaining = 2;
    await page.goto("./");

    const alert = page.getByRole("alert");
    await expect(alert).toBeVisible();
    const retry = alert.getByRole("button", { name: "Try again" });
    await retry.focus();
    await expect(retry).toBeFocused();
    await retry.press("Enter");
    await expect(page.getByRole("region", { name: "Primary actions" })).toBeVisible();
  });
});

test.describe("administrator route accessibility smoke", () => {
  test.beforeEach(async ({ page }) => { await installAdminApi(page); });

  test("administrator confirmation controls are keyboard reachable", async ({ page }) => {
    await page.goto("./admin/overview");
    const confirmation = page.getByRole("region", { name: "Administrator confirmation" });
    await expect(confirmation).toBeVisible();
    const pin = confirmation.getByLabel("Administrator PIN");
    await pin.focus();
    await expect(pin).toBeFocused();
    await pin.fill("A12345");
    await pin.press("Tab");
    await expect(confirmation.getByRole("button", { name: "Enter Admin Center" })).toBeFocused();
  });

  for (const route of ADMIN_ROUTES) {
    test(`${route.heading} exposes a stable accessible administrator structure`, async ({ page }) => {
      await enterAdmin(page);
      await page.goto(route.path);
      await expectPageStructure(page, route.heading);
      const adminNavigation = page.getByRole("navigation", { name: "Administration navigation" });
      await expect(adminNavigation).toHaveCount(1);
      await expect(adminNavigation.getByRole("link", { name: route.current, exact: true }))
        .toHaveAttribute("aria-current", "page");
    });
  }

  test("administrator step-up dialog has a keyboard-reachable cancel path", async ({ page }) => {
    await page.goto("./admin/review-lab");
    await page.getByLabel("Administrator PIN").fill("A12345");
    await page.getByRole("button", { name: "Enter Admin Center" }).click();
    await page.getByRole("button", { name: /Open Review Lab/ }).click();

    const dialog = page.getByRole("dialog", { name: "Confirm Review Lab launch" });
    await expect(dialog).toBeVisible();
    const cancel = dialog.getByRole("button", { name: "Cancel" });
    await cancel.focus();
    await expect(cancel).toBeFocused();
    await cancel.press("Enter");
    await expect(dialog).toHaveCount(0);
  });
});
