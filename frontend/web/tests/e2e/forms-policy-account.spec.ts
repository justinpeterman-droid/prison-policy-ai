import { expect, test } from "@playwright/test";
import { installOfficerApi } from "./support/mock-api";

test.beforeEach(async ({ page }) => {
  await installOfficerApi(page);
  await page.goto("./");
});

test("Forms Library previews a mixed selection without digitizing physical paperwork", async ({ page }) => {
  await page.getByRole("link", { name: "Open Forms Library" }).click();
  await expect(page.getByRole("heading", { name: "Forms Library" })).toBeVisible();

  await page.getByLabel("Select Medical Documentation Checklist").check();
  await page.getByLabel("Select Chain of Custody").check();
  await page.getByRole("button", { name: "Preview selected" }).click();

  const inspector = page.getByRole("complementary", { name: "Selected forms review" });
  await expect(inspector).toBeVisible();
  await expect(inspector).toContainText("Medical Documentation Checklist");
  await expect(inspector).toContainText("Chain of Custody");
  await expect(inspector).toContainText("Physical forms are not included in digital output");

  const physical = page.getByRole("article", { name: "Chain of Custody" });
  await expect(physical.getByText("PHYSICAL CARBON-COPY FORM REQUIRED")).toBeVisible();
  await expect(physical.getByRole("button", { name: /Print/i })).toHaveCount(0);
  await expect(physical.getByRole("button", { name: /download/i })).toHaveCount(0);
});

test("Policy Expert returns a cited answer without altering an incident", async ({ page }) => {
  await page.getByRole("link", { name: "Ask a Policy Question" }).click();
  await page.getByLabel("Policy question").fill(
    "What fictional supervisory review is required?",
  );
  await page.getByRole("button", { name: "Ask Policy Expert" }).click();

  await expect(page.getByRole("region", { name: "Policy answer" })).toContainText(
    "documented supervisory review",
  );
  await expect(page.getByRole("region", { name: "Policy sources" })).toContainText(
    "Fictional Operations Policy",
  );
  await expect(page.getByText(/does not add or change facts in an incident/i)).toBeVisible();
});

test("Account changes the PIN and revokes a different browser session", async ({ page }) => {
  await page.getByRole("link", { name: "Account" }).click();
  await expect(page.getByRole("heading", { name: "My Account" })).toBeVisible();
  await expect(page.getByText("F-1001")).toBeVisible();

  await page.getByLabel("Current PIN").fill("Q7W9E2");
  await page.getByLabel("New PIN").fill("A1B2C3");
  await page.getByLabel("Confirm new PIN").fill("A1B2C3");
  await page.getByRole("button", { name: "Change PIN" }).click();
  await expect(page.getByText(/PIN changed/i)).toBeVisible();

  const other = page.getByRole("article", { name: "Training laptop" });
  await expect(other).toBeVisible();
  await other.getByRole("button", { name: "Sign out Training laptop" }).click();
  await expect(other).toHaveCount(0);
  await expect(page.getByText("Current session")).toBeVisible();
});
