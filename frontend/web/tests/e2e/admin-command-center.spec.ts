import { expect, test, type Page } from "@playwright/test";
import { installAdminApi } from "./support/admin-mock-api";

async function enterAdmin(page: Page, path = "./admin/overview") {
  await page.goto(path);
  await expect(page.getByRole("heading", { name: "Administrator confirmation" })).toBeVisible();
  await page.getByLabel("Administrator PIN").fill("A12345");
  await page.getByRole("button", { name: "Enter Admin Center" }).click();
  await expect(page.getByRole("navigation", { name: "Administration navigation" })).toBeVisible();
}

test.beforeEach(async ({ page }) => {
  await installAdminApi(page);
});

test("command center keeps operations readable and action-oriented at 1366x768", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await enterAdmin(page);

  await expect(page.getByRole("heading", { name: /Good evening, Captain Blake/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Operational Command Center" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Today’s Paperwork" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Incidents Needing Attention" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Account Conditions" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "System Availability" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recent Administrative Activity" })).toBeVisible();
  await expect(page.getByText("Fictional Training Incident")).toBeVisible();
  await expect(page.getByText("Administrator context")).toBeVisible();

  const horizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2);
  expect(horizontalOverflow).toBe(false);
});

test("admin can move from all incidents into attributed controls and Document Studio", async ({ page }) => {
  await enterAdmin(page);
  await page.getByRole("link", { name: "All Incidents" }).click();

  await expect(page.getByRole("heading", { name: "All Incidents" })).toBeVisible();
  const incidentRow = page.getByRole("link", { name: /2026-08-029 Fictional Training Incident/ });
  await expect(incidentRow).toBeVisible();
  await expect(incidentRow.getByText("Ready to review")).toBeVisible();
  await expect(incidentRow.getByText("in progress")).toBeVisible();

  await incidentRow.click();
  await expect(page.getByRole("note", { name: "Administrator attribution notice" })).toContainText("every saved change");
  const adminControls = page.getByRole("region", { name: "Administrator incident controls" });
  await expect(adminControls).toBeVisible();
  await expect(page.getByLabel("Records status")).toHaveValue("in_progress");
  await expect(adminControls.getByText("Revision 4", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Fictional Training Incident" }).last()).toBeVisible();
});

test("accounts audit and health remain distinct operational surfaces", async ({ page }) => {
  await enterAdmin(page);
  const nav = page.getByRole("navigation", { name: "Administration navigation" });

  await nav.getByRole("link", { name: "Accounts & Staff" }).click();
  await expect(page.getByRole("heading", { name: "Accounts & Staff" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Officer Casey Morgan" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Linked Account" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Active Sessions" })).toBeVisible();
  await expect(page.getByText("Training laptop")).toBeVisible();

  await nav.getByRole("link", { name: "Audit Log" }).click();
  await expect(page.getByRole("heading", { name: "Audit Log" })).toBeVisible();
  const auditEvents = page.getByRole("region", { name: "Audit events" });
  await expect(auditEvents.getByText(/Staff Updated/)).toBeVisible();
  await expect(auditEvents.getByText(/narrative/i)).toHaveCount(0);

  await nav.getByRole("link", { name: "System Health" }).click();
  await expect(page.getByRole("heading", { name: "System Health" })).toBeVisible();
  await expect(page.getByText("Operational").first()).toBeVisible();
  await expect(page.getByText("Backup restore verification is not exposed in this workspace.")).toBeVisible();
});

test("mobile admin navigation stays usable and reduced motion removes travel", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await enterAdmin(page);

  const nav = page.getByRole("navigation", { name: "Administration navigation" });
  await expect(nav.getByRole("link", { name: "Overview" })).toBeVisible();
  await nav.getByRole("link", { name: "Review Lab" }).click();
  await expect(page.getByRole("heading", { name: "Review Lab" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Open Review Lab/ })).toBeVisible();

  const horizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2);
  expect(horizontalOverflow).toBe(false);
});
