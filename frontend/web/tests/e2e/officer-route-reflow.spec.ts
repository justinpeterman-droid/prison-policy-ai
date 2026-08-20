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

test.describe("Forms Library mobile guidance", () => {
  test.beforeEach(async ({ page }) => {
    await installOfficerApi(page);
    await page.setViewportSize({ width: 390, height: 844 });
  });

  test("separates guidance labels from their values without changing desktop copy", async ({ page }) => {
    await page.goto("./forms");
    const card = page.getByRole("article", { name: "Medical Documentation Checklist" });
    const guidance = card.locator(".forms-library-guidance p");
    await expect(guidance).toHaveCount(2);

    for (const paragraph of await guidance.all()) {
      const separated = await paragraph.evaluate((element) => {
        const label = element.querySelector("strong");
        const value = Array.from(element.childNodes).find((node) => (
          node.nodeType === Node.TEXT_NODE && node.textContent?.trim()
        ));
        if (!label || !value) return false;
        const range = document.createRange();
        range.selectNodeContents(value);
        return range.getBoundingClientRect().top >= label.getBoundingClientRect().bottom;
      });
      expect(separated, "guidance value should begin below its label on mobile").toBe(true);
    }
  });

  test("provides a 44 pixel mobile selection target with a visible checkbox", async ({ page }) => {
    await page.goto("./forms");
    const card = page.getByRole("article", { name: "Medical Documentation Checklist" });
    const target = card.locator(".forms-library-select");
    const checkbox = card.getByRole("checkbox", { name: "Select Medical Documentation Checklist" });

    await expectTouchTarget(target);
    const checkboxBox = await checkbox.boundingBox();
    expect(checkboxBox).not.toBeNull();
    expect(checkboxBox!.width).toBeGreaterThanOrEqual(20);
    expect(checkboxBox!.height).toBeGreaterThanOrEqual(20);
  });
});

test.describe("Document Studio tablet navigation targets", () => {
  test.beforeEach(async ({ page }) => {
    await installOfficerApi(page);
    await page.setViewportSize({ width: 768, height: 1024 });
  });

  test("keeps every document-area tab at least 44 pixels high", async ({ page }) => {
    await page.goto("./reports/00000000-0000-4000-8000-000000000010");
    const tabs = page.getByRole("tablist", { name: "Incident document areas" }).getByRole("tab");
    await expect(tabs).toHaveCount(6);

    for (const tab of await tabs.all()) {
      const box = await tab.boundingBox();
      expect(box, "tablet tab must have a measurable box").not.toBeNull();
      expect(box!.height, "tablet tab must be at least 44 CSS pixels high").toBeGreaterThanOrEqual(44);
    }
  });
});

test.describe("Document Studio mobile preview control", () => {
  test("keeps the close icon centered in a focused 44 pixel target", async ({ page }) => {
    const officerApiState = await installOfficerApi(page);
    officerApiState.showIncidentPaperwork = true;
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("./reports/00000000-0000-4000-8000-000000000010");
    await page.getByRole("tab", { name: "Required Paperwork" }).click();
    await page.getByRole("button", { name: "Preview Medical Documentation Checklist" }).click();

    const close = page.getByRole("button", { name: "Close form preview" });
    await close.focus();
    await page.keyboard.press("Shift+Tab");
    await page.keyboard.press("Tab");
    await expect(close).toBeFocused();
    const rendered = await close.evaluate((button) => {
      const target = button.getBoundingClientRect();
      const icon = button.querySelector("svg")!.getBoundingClientRect();
      const style = getComputedStyle(button);
      return {
        width: target.width,
        height: target.height,
        horizontalOffset: Math.abs((target.left + target.width / 2) - (icon.left + icon.width / 2)),
        verticalOffset: Math.abs((target.top + target.height / 2) - (icon.top + icon.height / 2)),
        outlineStyle: style.outlineStyle,
        outlineWidth: Number.parseFloat(style.outlineWidth),
      };
    });

    expect(rendered.width).toBeGreaterThanOrEqual(44);
    expect(rendered.height).toBeGreaterThanOrEqual(44);
    expect(rendered.horizontalOffset).toBeLessThanOrEqual(1);
    expect(rendered.verticalOffset).toBeLessThanOrEqual(1);
    expect(rendered.outlineStyle).not.toBe("none");
    expect(rendered.outlineWidth).toBeGreaterThanOrEqual(3);
  });
});

test.describe("Document Studio mobile tab reachability", () => {
  test.beforeEach(async ({ page }) => {
    await installOfficerApi(page);
    await page.setViewportSize({ width: 390, height: 844 });
  });

  test("keeps every horizontally scrollable document area keyboard reachable", async ({ page }) => {
    await page.goto("./reports/00000000-0000-4000-8000-000000000010");
    const tablist = page.getByRole("tablist", { name: "Incident document areas" });
    const history = tablist.getByRole("tab", { name: "History", exact: true });

    await history.focus();
    await expect(history).toBeFocused();
    await expect(history).toBeInViewport();
    await expectRenderedFocusIndicator(history);
    await history.press("Enter");
    await expect(history).toHaveAttribute("aria-selected", "true");
    await expect(page.getByRole("heading", { name: "Incident revisions" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Report revisions" })).toBeVisible();
    await expectNoPageOverflow(page);
  });
});
