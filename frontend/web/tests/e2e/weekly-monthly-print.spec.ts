import { expect, test, type Page } from "@playwright/test";
import { installAdminApi } from "./support/admin-mock-api";

async function enterAdmin(page: Page) {
  await page.goto("./admin/paperwork?tab=daily&work_date=2026-08-20&shift=D");
  await page.getByLabel("Administrator PIN").fill("A12345");
  await page.getByRole("button", { name: "Enter Admin Center" }).click();
  await expect(page.getByRole("heading", { name: "Paperwork Center" })).toBeVisible();
}

test.beforeEach(async ({ page }) => { await installAdminApi(page); });

test("weekly remains explicitly empty and monthly renders a printable four-form packet", async ({ page }) => {
  await enterAdmin(page);

  await page.getByRole("tab", { name: "Weekly" }).click();
  await expect(page.getByText("No weekly forms have been published.")).toBeVisible();
  await expect(page.getByRole("article")).toHaveCount(0);

  await page.getByRole("tab", { name: "Monthly" }).click();
  for (const title of [
    "Windows, Bars & Doors Check Log",
    "Use of Chemical Agents Log",
    "Contraband Search Log — Standard Area Rotation",
    "Contraband Search Log — Expanded Area Rotation",
  ]) await expect(page.getByRole("heading", { name: title }).first()).toBeVisible();

  await page.getByLabel("Select Windows, Bars & Doors Check Log").check();
  await page.getByLabel("Select Use of Chemical Agents Log").check();
  await page.getByRole("button", { name: /Preview Monthly Packet/ }).click();
  await page.emulateMedia({ media: "print" });
  await expect(page.locator(".print-document")).toHaveCount(2);
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2)).toBe(false);
});

test("monthly packet selections keep 44px mobile targets and keyboard activation", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await enterAdmin(page);
  await page.getByRole("tab", { name: "Monthly" }).click();

  const selections = page.getByRole("checkbox", { name: /^Select / });
  await expect(selections).toHaveCount(4);
  for (const checkbox of await selections.all()) {
    const labelBox = await checkbox.locator("xpath=ancestor::label").boundingBox();
    const checkboxBox = await checkbox.boundingBox();
    expect(labelBox?.height).toBeGreaterThanOrEqual(44);
    expect(labelBox?.width).toBeGreaterThanOrEqual(44);
    expect(checkboxBox?.height).toBeGreaterThanOrEqual(20);
    expect(checkboxBox?.width).toBeGreaterThanOrEqual(20);
  }

  const firstSelection = selections.first();
  await firstSelection.focus();
  await expect(firstSelection).toBeFocused();
  await firstSelection.press("Space");
  await expect(firstSelection).toBeChecked();
});
