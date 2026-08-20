import { expect, test, type Download, type Page } from "@playwright/test";

const SEEDED_INCIDENT_ID = "00000000-0000-4000-8000-00000000b001";

async function signIn(page: Page, employeeNumber: string, pin: string) {
  await page.goto("/workspace");
  await expect(page.getByRole("heading", { name: "Sign in to continue" })).toBeVisible();
  await page.getByLabel("Employee number").fill(employeeNumber);
  await page.getByLabel("PIN").fill(pin);
  await page.getByRole("button", { name: "Sign in" }).click();
}

async function downloadedBytes(download: Download): Promise<number> {
  const stream = await download.createReadStream();
  let bytes = 0;
  for await (const chunk of stream) bytes += chunk.length;
  return bytes;
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.print = () => {
      document.documentElement.dataset.betaSmokePrintCalled = "true";
    };
  });
});

test("built officer workspace uses real sessions, persistence, print, and DOCX download", async ({ page }) => {
  const document = await page.goto("/workspace");
  expect(document?.status()).toBe(200);
  expect(document?.headers()["content-security-policy"]).toContain("default-src 'self'");

  await signIn(page, "TEST-1001", "Z9Y8X7");
  await expect(page.getByRole("heading", { name: "Officer Avery Morgan" })).toBeVisible();

  await page.goto(`/workspace/reports/${SEEDED_INCIDENT_ID}`);
  await expect(page.getByRole("heading", { name: "Fictional Beta Smoke Incident" })).toBeVisible();
  await page.getByRole("tab", { name: "Officer Reports" }).click();
  await page.getByRole("button", { name: /First Person.*Officer Avery Morgan/i }).click();
  const narrative = page.getByLabel("First Person narrative");
  await expect(narrative).toHaveValue("Fictional initial report narrative.");
  await narrative.fill("Fictional beta smoke revision. No operational information is used.");
  await page.getByRole("button", { name: "Save Report" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Saved to server" })).toBeVisible();

  await page.getByRole("button", { name: "Print" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-beta-smoke-print-called", "true");

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download Word" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.docx$/i);
  expect(await downloadedBytes(download)).toBeGreaterThan(1_000);

  await page.goto("/workspace/new-report");
  await page.getByLabel("Incident number").fill("2026-08-902");
  await page.getByLabel("Incident name").fill("Fictional Browser Smoke Incident");
  await page.getByLabel("Facility").fill("Fictional Training Unit");
  await page.getByLabel("Date").fill("2026-08-20");
  await page.getByLabel("Time").fill("11:30");
  await page.getByLabel("Location").fill("Training Hall");
  await page.getByLabel("Initial category, when known").fill("fictional incident");
  await page.getByRole("button", { name: "Continue to Field Notes" }).click();
  await page.getByLabel("Officer field notes").fill(
    "Fictional browser-smoke observations. Unknown details remain unknown.",
  );
  await page.getByRole("button", { name: "Save and Review Facts" }).click();
  await expect(page.getByRole("heading", { name: "Review Facts" })).toBeVisible();
  await page.getByRole("button", { name: "Confirm Facts and Continue" }).click();
  await page.getByRole("button", { name: "Save and Continue to Reports" }).click();
  await page.getByRole("button", { name: "Continue to Forms & Export" }).click();
  await expect(page.getByRole("link", { name: "Open Document Studio" })).toBeVisible();

  await page.goto("/workspace/count-sheet");
  await expect(page.getByRole("heading", { name: "NCU Days Count" })).toBeVisible();
  await page.getByRole("button", { name: "Save Count Sheet" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Saved to server" })).toBeVisible();
  await page.getByRole("button", { name: "Preview Print Layout" }).click();
  await expect(page.getByRole("dialog", { name: "Official landscape layout" })).toBeVisible();

  await page.goto("/workspace/policy-expert");
  await expect(page.getByRole("heading", { name: "Policy Expert" })).toBeVisible();
  await page.goto("/workspace/forms");
  await expect(page.getByRole("heading", { name: "Forms Library" })).toBeVisible();

  const visibleText = await page.locator("body").innerText();
  expect(visibleText).not.toContain("Z9Y8X7");
  expect(visibleText).not.toContain("beta-smoke-identity-pepper");
  expect(visibleText).not.toContain("beta-smoke-cursor-signing-key");

  await page.getByRole("button", { name: "Officer Avery Morgan" }).click();
  await page.getByRole("menuitem", { name: "Sign out this device" }).click();
  await expect(page.getByRole("heading", { name: "Sign in to continue" })).toBeVisible();
});

test("built administrator workspace reaches Paperwork Center and preserves the legacy pilot fallback", async ({ page }) => {
  await signIn(page, "TEST-9001", "Q7W9E2");
  await expect(page.getByRole("heading", { name: "Officer Jordan Taylor" })).toBeVisible();
  await page.goto("/workspace/admin/paperwork");
  await expect(page.getByRole("heading", { name: "Administrator confirmation" })).toBeVisible();
  await page.getByLabel("Administrator PIN").fill("Q7W9E2");
  await page.getByRole("button", { name: "Enter Admin Center" }).click();
  await expect(page.getByRole("heading", { name: "Paperwork Center" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Daily" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Weekly" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Monthly" })).toBeVisible();

  await page.getByRole("button", { name: "Officer Jordan Taylor" }).click();
  await page.getByRole("menuitem", { name: "Sign out this device" }).click();
  await expect(page.getByRole("heading", { name: "Sign in to continue" })).toBeVisible();

  const legacy = await page.goto("/reports?code=fictional-beta-access");
  expect(legacy?.status()).toBe(200);
  await expect(page.locator("[data-legacy-pilot-warning='true']")).toContainText(
    "Pilot fallback: legacy reports are transient and are not centralized history.",
  );
});
