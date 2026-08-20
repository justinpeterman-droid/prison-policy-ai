import { expect, test, type Page } from "@playwright/test";
import { installAdminApi } from "./support/admin-mock-api";

async function enterAdmin(page: Page) {
  await page.goto("./admin/paperwork?tab=daily&work_date=2026-08-20&shift=D");
  await page.getByLabel("Administrator PIN").fill("A12345");
  await page.getByRole("button", { name: "Enter Admin Center" }).click();
  await expect(page.getByRole("heading", { name: "Paperwork Center" })).toBeVisible();
}

test.beforeEach(async ({ page }) => { await installAdminApi(page); });

test("all six daily print documents render at their approved hierarchy without screen overflow", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await enterAdmin(page);
  const forms = [
    ["assignment_roster", "Shift Assignment Roster", "assignment-roster-print"],
    ["uniform_inspection", "Uniform Inspection Log", "uniform-inspection-print"],
    ["metal_detector_test", "Daily Walk-Through Metal Detector Testing", "metal-detector-print"],
    ["perimeter_check", "Perimeter Check List", "perimeter-check-print"],
    ["random_search_log", "Random Searches Log", "random-searches-print"],
    ["detector_sign_out", "Handheld Metal Detector Sign-Out", "detector-signout-print"],
  ] as const;
  for (const [kind, title, testId] of forms) {
    await page.goto(`./admin/paperwork?tab=daily&work_date=2026-08-20&shift=D&kind=${kind}`);
    await expect(page.getByRole("heading", { name: title, level: 1 })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2)).toBe(false);
    await page.emulateMedia({ media: "print" });
    await expect(page.getByTestId(testId).first()).toBeVisible();
    const text = await page.getByTestId(testId).first().innerText();
    expect(text.length).toBeGreaterThan(80);
    await page.emulateMedia({ media: "screen" });
  }
});

test("daily forms keep usable mobile structure and named print page orientation", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await enterAdmin(page);
  await page.goto("./admin/paperwork?tab=daily&work_date=2026-08-20&shift=D&kind=metal_detector_test");
  await expect(page.getByLabel("Mobile detector", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2)).toBe(false);
  await page.goto("./admin/paperwork?tab=daily&work_date=2026-08-20&shift=D&kind=perimeter_check");
  await expect(page.getByRole("group", { name: "Doors", exact: true })).toBeVisible();
  const pageRules = await page.evaluate(() => Array.from(document.styleSheets).flatMap((sheet) => {
    try { return Array.from(sheet.cssRules).map((rule) => rule.cssText); } catch { return []; }
  }).join("\n"));
  expect(pageRules).toContain("perimeter-check");
  expect(pageRules).toContain("portrait");
});

test("random-search section links keep mobile target, focus, and keyboard-order contracts", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await enterAdmin(page);
  await page.goto("./admin/paperwork?tab=daily&work_date=2026-08-20&shift=D&kind=random_search_log");

  const navigation = page.getByRole("navigation", { name: "Random search sections" });
  const links = navigation.getByRole("link");
  await expect(links).toHaveCount(4);
  await expect(links).toHaveText(["North 1", "North 2", "South 1", "South 2"]);

  for (const link of await links.all()) {
    const geometry = await link.evaluate((element) => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return {
        height: rect.height,
        alignItems: style.alignItems,
        justifyContent: style.justifyContent,
      };
    });
    expect(geometry.height).toBeGreaterThanOrEqual(44);
    expect(geometry.alignItems).toBe("center");
    expect(geometry.justifyContent).toBe("center");
  }

  const first = links.first();
  await first.focus();
  await expect(first).toBeFocused();
  const focus = await first.evaluate((element) => {
    const style = getComputedStyle(element);
    const link = element.getBoundingClientRect();
    const nav = element.parentElement!.getBoundingClientRect();
    const outward = Number.parseFloat(style.outlineWidth) + Number.parseFloat(style.outlineOffset);
    return {
      outlineStyle: style.outlineStyle,
      outlineWidth: Number.parseFloat(style.outlineWidth),
      contained: link.left - outward >= nav.left - 0.5 && link.top - outward >= nav.top - 0.5,
    };
  });
  expect(focus.outlineStyle).not.toBe("none");
  expect(focus.outlineWidth).toBeGreaterThanOrEqual(3);
  expect(focus.contained).toBe(true);

  await first.press("Tab");
  await expect(links.nth(1)).toBeFocused();
});
