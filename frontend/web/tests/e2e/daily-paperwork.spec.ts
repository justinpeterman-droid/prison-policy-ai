import { expect, test, type Page } from "@playwright/test";
import { installAdminApi } from "./support/admin-mock-api";


async function enterAdmin(page: Page) {
  await page.goto("./admin/paperwork?tab=daily&work_date=2026-08-20&shift=D");
  await page.getByLabel("Administrator PIN").fill("A12345");
  await page.getByRole("button", { name: "Enter Admin Center" }).click();
  await expect(page.getByRole("heading", { name: "Paperwork Center" })).toBeVisible();
}


test.beforeEach(async ({ page }) => { await installAdminApi(page); });


test("daily paperwork saves, reopens, preserves a failed edit, and retries without data loss", async ({ page }) => {
  await enterAdmin(page);
  await page.goto("./admin/paperwork?tab=daily&work_date=2026-08-20&shift=D&kind=detector_sign_out");

  const area = page.getByLabel("D1 area of assignment");
  await area.fill("North Hall");
  await page.getByRole("button", { name: "Save detector sign-out" }).click();
  await expect(page.locator(".daily-save-state")).toHaveText("Saved");
  await expect(page).toHaveURL(/record_id=00000000-0000-4000-8000-000000000971/);

  await page.reload();
  await expect(area).toHaveValue("North Hall");

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
  await expect(page.locator(".daily-save-state")).toHaveText("Save failed—work preserved");
  await expect(page.getByRole("alert")).toContainText("Fictional temporary save outage");
  await expect(area).toHaveValue("North Hall Annex");

  await page.getByRole("button", { name: "Save detector sign-out" }).click();
  await expect(page.locator(".daily-save-state")).toHaveText("Saved");
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
