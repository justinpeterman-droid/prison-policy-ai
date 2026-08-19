import { expect, test } from "@playwright/test";
import { installOfficerApi } from "./support/mock-api";

test.beforeEach(async ({ page }) => {
  await installOfficerApi(page);
  await page.goto("./");
});

test("Forms Library previews a mixed selection without digitizing physical paperwork", async ({ page }) => {
  await page.getByRole("link", { name: "Open Forms Library", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Forms Library", exact: true })).toBeVisible();

  await page.getByLabel("Select Medical Documentation Checklist", { exact: true }).check();
  await page.getByLabel("Select Chain of Custody", { exact: true }).check();
  await page.getByRole("button", { name: "Preview selected", exact: true }).click();

  const inspector = page.getByRole("complementary", { name: "Selected forms review", exact: true });
  await expect(inspector).toBeVisible();
  await expect(inspector).toContainText("Medical Documentation Checklist");
  await expect(inspector).toContainText("Chain of Custody");
  await expect(inspector).toContainText("Physical forms are not included in digital output");

  const physical = page.getByRole("article", { name: "Chain of Custody", exact: true });
  await expect(physical.getByText("PHYSICAL CARBON-COPY FORM REQUIRED", { exact: true })).toBeVisible();
  await expect(physical.getByRole("button", { name: /Print/i })).toHaveCount(0);
  await expect(physical.getByRole("button", { name: /download/i })).toHaveCount(0);
});

test("Policy Expert returns a cited answer without altering an incident", async ({ page }) => {
  await page.getByRole("link", { name: "Ask a Policy Question", exact: true }).click();
  await page.getByLabel("Policy question", { exact: true }).fill(
    "What fictional supervisory review is required?",
  );
  await page.getByRole("button", { name: "Ask Policy Expert", exact: true }).click();

  await expect(page.getByRole("region", { name: "Policy answer", exact: true })).toContainText(
    "documented supervisory review",
  );
  await expect(page.getByRole("region", { name: "Policy sources", exact: true })).toContainText(
    "Fictional Operations Policy",
  );
  await expect(page.getByText(/does not add or change facts in an incident/i)).toBeVisible();
});

test("Account changes the PIN and revokes a different browser session", async ({ page }) => {
  await page.getByRole("link", { name: "Account", exact: true }).click();
  await expect(page.getByRole("heading", { name: "My Account", exact: true })).toBeVisible();
  await expect(page.getByText("F-1001", { exact: true })).toBeVisible();

  await page.getByLabel("Current PIN", { exact: true }).fill("Q7W9E2");
  await page.getByLabel("New PIN", { exact: true }).fill("A1B2C3");
  await page.getByLabel("Confirm new PIN", { exact: true }).fill("A1B2C3");
  await page.getByRole("button", { name: "Change PIN", exact: true }).click();
  await expect(page.getByText(/PIN changed/i)).toBeVisible();

  const other = page.getByRole("article", { name: "Training laptop", exact: true });
  await expect(other).toBeVisible();
  await other.getByRole("button", { name: "Sign out Training laptop", exact: true }).click();
  await expect(other).toHaveCount(0);
  await expect(page.getByText("Current session", { exact: true })).toBeVisible();
});
