import { expect, test, type Page } from "@playwright/test";
import { installAdminApi } from "./support/admin-mock-api";


async function enterAdmin(page: Page) {
  await page.goto("./admin/paperwork?tab=daily&work_date=2026-08-20&shift=D");
  await page.getByLabel("Administrator PIN").fill("A12345");
  await page.getByRole("button", { name: "Enter Admin Center" }).click();
  await expect(page.getByRole("heading", { name: "Paperwork Center" })).toBeVisible();
}


test.beforeEach(async ({ page }) => { await installAdminApi(page); });


test("daily paperwork distinguishes reconnecting from server failure and retries without data loss", async ({ page }) => {
  await enterAdmin(page);
  await page.goto("./admin/paperwork?tab=daily&work_date=2026-08-20&shift=D&kind=detector_sign_out");

  const area = page.getByLabel("D1 area of assignment");
  await area.fill("North Hall");
  await page.getByRole("button", { name: "Save detector sign-out" }).click();
  await expect(page.locator(".daily-save-state")).toHaveText("Saved to server");
  await expect(page).toHaveURL(/record_id=00000000-0000-4000-8000-000000000971/);

  await page.reload();
  await expect(area).toHaveValue("North Hall");

  await area.fill("North Hall West");
  await page.route(
    /\/api\/web\/v1\/admin\/paperwork\/daily\/detector_sign_out\/[^/]+$/,
    async (route) => { await route.abort("failed"); },
    { times: 1 },
  );
  await page.getByRole("button", { name: "Save detector sign-out" }).click();
  await expect(page.locator(".daily-save-state")).toHaveText(
    "Reconnecting — changes remain visible; server save not confirmed",
  );
  await expect(page.getByRole("alert")).toContainText("The service could not be reached");
  await expect(area).toHaveValue("North Hall West");

  await page.getByRole("button", { name: "Save detector sign-out" }).click();
  await expect(page.locator(".daily-save-state")).toHaveText("Saved to server");
  await page.reload();
  await expect(area).toHaveValue("North Hall West");

  await area.fill("North Hall Annex");
  await page.route(
    /\/api\/web\/v1\/admin\/paperwork\/daily\/detector_sign_out\/[^/]+$/,
    async (route) => {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        headers: { "X-Request-ID": "daily-e2e-failure" },
        body: JSON.stringify({
          error: {
            code: "dependency_unavailable",
            message: "Fictional temporary save outage.",
            retryable: true,
            details: {},
          },
          request_id: "daily-e2e-failure",
        }),
      });
    },
    { times: 1 },
  );
  await page.getByRole("button", { name: "Save detector sign-out" }).click();
  await expect(page.locator(".daily-save-state")).toHaveText("Save failed — changes remain visible; server save not confirmed");
  await expect(page.getByRole("alert")).toContainText("Fictional temporary save outage");
  await expect(area).toHaveValue("North Hall Annex");

  await page.getByRole("button", { name: "Save detector sign-out" }).click();
  await expect(page.locator(".daily-save-state")).toHaveText("Saved to server");
  await page.reload();
  await expect(area).toHaveValue("North Hall Annex");
});


test("paperwork periods and detector matrix support keyboard-only navigation", async ({ page }) => {
  await enterAdmin(page);
  const daily = page.getByRole("tab", { name: "Daily" });
  const weekly = page.getByRole("tab", { name: "Weekly" });
  const monthly = page.getByRole("tab", { name: "Monthly" });

  await daily.focus();
  await daily.press("ArrowRight");
  await expect(weekly).toBeFocused();
  await expect(weekly).toHaveAttribute("aria-selected", "true");
  await weekly.press("End");
  await expect(monthly).toBeFocused();
  await monthly.press("Home");
  await expect(daily).toBeFocused();

  await page.goto("./admin/paperwork?tab=daily&work_date=2026-08-20&shift=D&kind=metal_detector_test");
  const firstCell = page.getByLabel("Detector 1 Position 1", { exact: true });
  const nextCell = page.getByLabel("Detector 2 Position 1", { exact: true });
  await firstCell.focus();
  await firstCell.press("ArrowRight");
  await expect(nextCell).toBeFocused();
  await nextCell.press("ArrowLeft");
  await expect(firstCell).toBeFocused();
});

test("mobile roster reorder controls keep centered 44px targets and logical keyboard order", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await enterAdmin(page);
  await page.goto("./admin/paperwork?tab=daily&work_date=2026-08-20&shift=D&kind=assignment_roster");

  const controls = page.locator(".roster-reorder-controls").nth(1).getByRole("button");
  await expect(controls).toHaveCount(3);
  for (const control of await controls.all()) {
    const controlBox = await control.boundingBox();
    const iconBox = await control.locator("svg").boundingBox();
    expect(controlBox?.height).toBeGreaterThanOrEqual(44);
    expect(controlBox?.width).toBeGreaterThanOrEqual(44);
    expect(Math.abs((controlBox!.x + controlBox!.width / 2) - (iconBox!.x + iconBox!.width / 2))).toBeLessThanOrEqual(1);
    expect(Math.abs((controlBox!.y + controlBox!.height / 2) - (iconBox!.y + iconBox!.height / 2))).toBeLessThanOrEqual(1);
  }

  await controls.nth(0).focus();
  await controls.nth(0).press("Tab");
  await expect(controls.nth(1)).toBeFocused();
  await controls.nth(1).press("Tab");
  await expect(controls.nth(2)).toBeFocused();
});
