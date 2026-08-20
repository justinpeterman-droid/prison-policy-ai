import { expect, test, type Locator, type Page } from "@playwright/test";
import { installOfficerApi } from "./support/mock-api";

const REFLOW_ROUTES = [
  {
    name: "Forms Library",
    path: "./forms",
    primaryControl: (page: Page) => page.getByRole("searchbox", { name: "Search forms" }),
    action: (page: Page) => page.getByRole("button", {
      name: "Preview Medical Documentation Checklist",
      exact: true,
    }),
  },
  {
    name: "Policy Expert",
    path: "./policy-expert",
    primaryControl: (page: Page) => page.getByLabel("Policy question", { exact: true }),
    action: (page: Page) => page.getByRole("button", { name: "Ask Policy Expert", exact: true }),
  },
  {
    name: "My Account",
    path: "./account",
    primaryControl: (page: Page) => page.getByLabel("Current PIN", { exact: true }),
    action: (page: Page) => page.getByRole("button", { name: "Change PIN", exact: true }),
  },
] as const;

async function expectNoPageOverflow(page: Page): Promise<void> {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
    offenders: Array.from(document.querySelectorAll<HTMLElement>("body *"))
      .filter((element) => element.getBoundingClientRect().right > document.documentElement.clientWidth + 2)
      .slice(0, 8)
      .map((element) => `${element.tagName.toLowerCase()}.${element.className || "(no-class)"}`),
  }));
  expect(
    dimensions.scrollWidth,
    `page scroll width ${dimensions.scrollWidth}px exceeds its ${dimensions.clientWidth}px viewport; offenders: ${dimensions.offenders.join(", ")}`,
  ).toBeLessThanOrEqual(dimensions.clientWidth + 2);
}

async function scrollIntoView(locator: Locator): Promise<void> {
  await locator.evaluate((element) => element.scrollIntoView({ block: "center", inline: "nearest" }));
}

async function expectTouchTarget(locator: Locator): Promise<void> {
  const box = await locator.boundingBox();
  expect(box, "touch target must have a measurable box").not.toBeNull();
  expect(box!.width, "touch target must be at least 44 CSS pixels wide").toBeGreaterThanOrEqual(44);
  expect(box!.height, "touch target must be at least 44 CSS pixels tall").toBeGreaterThanOrEqual(44);
}

async function expectRenderedFocusIndicator(locator: Locator): Promise<void> {
  const indicator = await locator.evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      outlineStyle: style.outlineStyle,
      outlineWidth: Number.parseFloat(style.outlineWidth),
      boxShadow: style.boxShadow,
    };
  });
  expect(
    (indicator.outlineStyle !== "none" && indicator.outlineWidth > 0) || indicator.boxShadow !== "none",
    "focused primary action must render a visible outline or focus shadow",
  ).toBe(true);
}

test.describe("officer route text reflow", () => {
  test.beforeEach(async ({ page }) => {
    await installOfficerApi(page);
    await page.setViewportSize({ width: 390, height: 844 });
  });

  for (const scale of [200, 400] as const) {
    for (const route of REFLOW_ROUTES) {
      test(`${route.name} preserves primary controls at ${scale} percent text sizing`, async ({ page }) => {
        await page.goto(route.path);
        await page.evaluate((percentage) => {
          document.documentElement.style.fontSize = `${percentage}%`;
        }, scale);

        await expect(page.getByRole("heading", { name: route.name, level: 1, exact: true })).toBeVisible();
        const control = route.primaryControl(page);
        await scrollIntoView(control);
        await expect(control).toBeVisible();
        const action = route.action(page);
        await scrollIntoView(action);
        await expect(action).toBeVisible();
        await expectNoPageOverflow(page);
      });
    }
  }
});

test.describe("officer route short-height keyboard pressure", () => {
  test.beforeEach(async ({ page }) => {
    await installOfficerApi(page);
    // Headless Chromium cannot summon a platform virtual keyboard. A short
    // visual viewport exercises the same vertical-space and sticky-control risk.
    await page.setViewportSize({ width: 390, height: 420 });
  });

  for (const route of REFLOW_ROUTES) {
    test(`${route.name} keeps its focused field and primary action reachable`, async ({ page }) => {
      await page.goto(route.path);
      const control = route.primaryControl(page);
      await scrollIntoView(control);
      await control.focus();
      await expect(control).toBeFocused();
      await expectTouchTarget(control);

      const action = route.action(page);
      await scrollIntoView(action);
      await expect(action).toBeVisible();
      await expectTouchTarget(action);
      await action.focus();
      await expect(action).toBeFocused();
      await expectRenderedFocusIndicator(action);
      await expectNoPageOverflow(page);
    });
  }
});
