import { expect, test } from "@playwright/test";
import { installOfficerApi } from "./support/mock-api";

test.beforeEach(async ({ page }) => {
  await installOfficerApi(page);
  await page.goto("./");
  await page.getByRole("region", { name: "Primary actions" })
    .getByRole("link", { name: "Open Count Sheet", exact: true })
    .click();
  await expect(page.getByRole("heading", { name: "NCU Days Count", exact: true })).toBeVisible();
});

test("Count Sheet calculates, saves, reopens, and prints without balancing values", async ({ page }) => {
  await expect(page.getByRole("region", { name: "Count Sheet entry grid" })).toBeVisible();
  const area = page.getByLabel("A/W Office, column 1", { exact: true });
  const inHousing = page.getByLabel("In housing, column 1", { exact: true });
  const operational = page.getByLabel("Operational total: on site", { exact: true });

  await area.fill("4");
  await inHousing.fill("6");
  await operational.fill("8");
  await expect(page.getByText("The totals differ by 2.", { exact: true })).toBeVisible();
  await expect(area).toHaveValue("4");

  await operational.fill("10");
  await expect(page.getByText("Housing and operational totals agree.", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Save Count Sheet", exact: true }).click();
  await expect(page.getByText("Saved", { exact: true })).toBeVisible();

  await page.reload();
  await expect(page.getByLabel("A/W Office, column 1", { exact: true })).toHaveValue("4");
  await expect(page.getByText("Revision 1", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Preview Print Layout", exact: true }).click();
  const preview = page.getByRole("dialog", { name: "Official landscape layout", exact: true });
  await expect(preview).toBeVisible();
  await expect(preview.getByLabel("Count Sheet print preview", { exact: true })).toContainText("COUNT RECONCILED");

  await page.emulateMedia({ media: "print" });
  await expect(page.getByLabel("Count Sheet print preview", { exact: true }).last()).toBeVisible();
});

test("Count Sheet keyboard movement follows the official grid", async ({ page }) => {
  const first = page.getByLabel("A/W Office, column 1", { exact: true });
  const right = page.getByLabel("A/W Office, column 2", { exact: true });
  const below = page.getByLabel("Barber Shop I/M, column 2", { exact: true });

  await first.focus();
  await first.press("ArrowRight");
  await expect(right).toBeFocused();
  await right.press("Enter");
  await expect(below).toBeFocused();
  await below.press("Shift+Enter");
  await expect(right).toBeFocused();
});

test("mobile Count Sheet keeps totals and grouped housing entry visible", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();

  await expect(page.getByRole("heading", { name: "Housing 1", exact: true })).toBeVisible();
  await expect(page.getByLabel("Persistent count totals", { exact: true })).toBeVisible();
  await page.getByLabel("A/W Office, column 1", { exact: true }).fill("2");
  await expect(page.getByLabel("Persistent count totals", { exact: true })).toContainText("Housing 2");
});
