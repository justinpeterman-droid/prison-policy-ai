import { expect, test } from "@playwright/test";
import { installOfficerApi } from "./support/mock-api";


test.beforeEach(async ({ page }) => {
  await installOfficerApi(page);
});

test("normal officers cannot discover or enter administrator routes", async ({ page }) => {
  await page.goto("./");
  await expect(page.getByRole("link", { name: "Administration" })).toHaveCount(0);

  await page.goto("./admin/overview");
  await expect(page.getByRole("heading", { name: "Workspace page not found" })).toBeVisible();
  await expect(page.getByText("Operational Command Center")).toHaveCount(0);
});
