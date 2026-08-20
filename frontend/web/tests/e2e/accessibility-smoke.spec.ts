import { expect, test, type Locator, type Page } from "@playwright/test";
import { installAdminApi } from "./support/admin-mock-api";
import { installOfficerApi, type OfficerApiState } from "./support/mock-api";

const OFFICER_ROUTES = [
  { path: "./", heading: "Officer Casey Morgan", current: "Home" },
  { path: "./new-report", heading: "New Report", current: "New Report" },
  { path: "./reports", heading: "Reports", current: "Reports" },
  { path: "./policy-expert", heading: "Policy Expert", current: "Policy Expert" },
  { path: "./forms", heading: "Forms Library", current: "Forms Library" },
  { path: "./account", heading: "My Account", current: "Account" },
  { path: "./count-sheet", heading: "NCU Days Count" },
] as const;

const ADMIN_ROUTES = [
  { path: "./admin/overview", heading: "Operational Command Center", current: "Overview" },
  { path: "./admin/incidents", heading: "All Incidents", current: "All Incidents" },
  { path: "./admin/paperwork?tab=daily&work_date=2026-08-20&shift=D", heading: "Paperwork Center", current: "Paperwork Center" },
  { path: "./admin/accounts-staff", heading: "Accounts & Staff", current: "Accounts & Staff" },
  { path: "./admin/audit", heading: "Audit Log", current: "Audit Log" },
  { path: "./admin/health", heading: "System Health", current: "System Health" },
  { path: "./admin/review-lab", heading: "Review Lab", current: "Review Lab" },
] as const;

async function expectNamedVisibleControls(page: Page): Promise<void> {
  const unnamed = await page.locator("input, select, textarea").evaluateAll((controls) => controls
    .filter((control) => {
      const element = control as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
      const style = getComputedStyle(element);
      const visible = style.display !== "none" && style.visibility !== "hidden" && element.getClientRects().length > 0;
      if (!visible || (element instanceof HTMLInputElement && element.type === "hidden")) return false;
      return !element.labels?.length
        && !element.getAttribute("aria-label")?.trim()
        && !element.getAttribute("aria-labelledby")?.trim()
        && !element.getAttribute("title")?.trim();
    })
    .map((control) => ({
      tag: control.tagName.toLowerCase(),
      type: control.getAttribute("type"),
      name: control.getAttribute("name"),
      placeholder: control.getAttribute("placeholder"),
    })));
  expect(unnamed, `Visible form controls need programmatic labels: ${JSON.stringify(unnamed)}`).toEqual([]);
}

async function expectSemanticIntegrity(page: Page): Promise<void> {
  const findings = await page.locator("body").evaluate((body) => {
    const visible = (element: Element): boolean => {
      const style = getComputedStyle(element);
      return style.display !== "none"
        && style.visibility !== "hidden"
        && element.getClientRects().length > 0;
    };
    const labelText = (element: Element): string => {
      const labelledBy = element.getAttribute("aria-labelledby")?.trim();
      if (labelledBy) {
        return labelledBy.split(/\s+/)
          .map((id) => document.getElementById(id)?.textContent ?? "")
          .join(" ")
          .trim();
      }
      const ariaLabel = element.getAttribute("aria-label")?.trim();
      if (ariaLabel) return ariaLabel;
      const imageAlt = element.querySelector("img[alt]")?.getAttribute("alt")?.trim();
      return `${element.textContent ?? ""} ${imageAlt ?? ""}`.trim();
    };
    const describe = (element: Element): string => {
      const id = element.id ? `#${element.id}` : "";
      const classes = typeof element.className === "string"
        ? element.className.trim().split(/\s+/).filter(Boolean).slice(0, 2).map((name) => `.${name}`).join("")
        : "";
      return `${element.tagName.toLowerCase()}${id}${classes}`;
    };
    const issues: string[] = [];
    const ids = new Map<string, Element[]>();

    for (const element of body.querySelectorAll("[id]")) {
      const id = element.id.trim();
      if (!id) continue;
      const matches = ids.get(id) ?? [];
      matches.push(element);
      ids.set(id, matches);
    }
    for (const [id, matches] of ids) {
      if (matches.length > 1) issues.push(`duplicate id #${id} (${matches.length})`);
    }

    for (const element of body.querySelectorAll("button, a[href]")) {
      if (!visible(element) || element.getAttribute("aria-hidden") === "true") continue;
      if (!labelText(element)) issues.push(`${describe(element)} has no accessible name`);
    }

    for (const image of body.querySelectorAll("img")) {
      if (!visible(image) || image.getAttribute("aria-hidden") === "true") continue;
      if (!image.hasAttribute("alt")) issues.push(`${describe(image)} has no alt attribute`);
    }

    for (const element of body.querySelectorAll("[aria-labelledby], [aria-describedby], [aria-errormessage]")) {
      for (const attribute of ["aria-labelledby", "aria-describedby", "aria-errormessage"] as const) {
        const value = element.getAttribute(attribute)?.trim();
        if (!value) continue;
        for (const id of value.split(/\s+/)) {
          if (!document.getElementById(id)) issues.push(`${describe(element)} has broken ${attribute}=#${id}`);
        }
      }
    }

    for (const element of body.querySelectorAll("[tabindex]")) {
      if (Number(element.getAttribute("tabindex")) > 0) {
        issues.push(`${describe(element)} uses positive tabindex`);
      }
    }

    for (const element of body.querySelectorAll("button, a[href], input:not([type=hidden]), select, textarea")) {
      const ancestor = element.parentElement?.closest("button, a[href], input, select, textarea");
      if (ancestor) issues.push(`${describe(element)} is nested inside ${describe(ancestor)}`);
    }
    return issues;
  });
  expect(findings, `Automated semantic accessibility findings:\n${findings.join("\n")}`).toEqual([]);
}

async function expectFocusIndicatorUnclipped(locator: Locator): Promise<void> {
  const result = await locator.evaluate((element) => {
    const target = element as HTMLElement;
    const style = getComputedStyle(target);
    const outline = style.outlineStyle !== "none" ? Number.parseFloat(style.outlineWidth) : 0;
    const offset = Number.parseFloat(style.outlineOffset) || 0;
    const inset = Math.max(0, outline + offset);
    const rect = target.getBoundingClientRect();
    const focusRect = {
      left: rect.left - inset,
      top: rect.top - inset,
      right: rect.right + inset,
      bottom: rect.bottom + inset,
    };
    const clippedBy: string[] = [];
    for (let ancestor = target.parentElement; ancestor; ancestor = ancestor.parentElement) {
      const ancestorStyle = getComputedStyle(ancestor);
      if (![ancestorStyle.overflow, ancestorStyle.overflowX, ancestorStyle.overflowY]
        .some((value) => value === "hidden" || value === "clip")) continue;
      const bounds = ancestor.getBoundingClientRect();
      if (focusRect.left < bounds.left || focusRect.top < bounds.top
        || focusRect.right > bounds.right || focusRect.bottom > bounds.bottom) {
        clippedBy.push(`${ancestor.tagName.toLowerCase()}.${ancestor.className || "(no-class)"}`);
      }
    }
    return {
      hasIndicator: outline > 0 || style.boxShadow !== "none",
      outline,
      offset,
      targetRect: { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom },
      insideViewport: focusRect.left >= 0 && focusRect.top >= 0
        && focusRect.right <= innerWidth && focusRect.bottom <= innerHeight,
      focusRect,
      viewport: { width: innerWidth, height: innerHeight },
      clippedBy,
    };
  });
  expect(result.hasIndicator, "focused control must render an outline or focus shadow").toBe(true);
  expect(
    result.insideViewport,
    `focused control and its outline must remain inside the viewport: ${JSON.stringify({ targetRect: result.targetRect, outline: result.outline, offset: result.offset, focusRect: result.focusRect, viewport: result.viewport })}`,
  ).toBe(true);
  expect(result.clippedBy, "focused control outline must not be clipped by an ancestor").toEqual([]);
}

async function expectPageStructure(page: Page, heading: string): Promise<void> {
  await expect(page.getByRole("heading", { name: heading, level: 1, exact: true })).toBeVisible();
  await expect(page.getByRole("main")).toHaveCount(1);
  await expect(page.getByRole("navigation", { name: "Officer navigation" })).toHaveCount(1);
  await expectNamedVisibleControls(page);
  await expectSemanticIntegrity(page);
  await expect(page.locator("h1:visible")).toHaveCount(1);
}

async function enterAdmin(page: Page): Promise<void> {
  await page.goto("./admin/overview");
  await page.getByLabel("Administrator PIN").fill("A12345");
  await page.getByRole("button", { name: "Enter Admin Center" }).click();
  await expect(page.getByRole("navigation", { name: "Administration navigation" })).toBeVisible();
}

test.describe("officer route accessibility smoke", () => {
  let officerApiState: OfficerApiState;
  test.beforeEach(async ({ page }) => { officerApiState = await installOfficerApi(page); });

  for (const route of OFFICER_ROUTES) {
    test(`${route.heading} exposes a stable accessible page structure`, async ({ page }) => {
      await page.goto(route.path);
      await expectPageStructure(page, route.heading);
      if ("current" in route) {
        await expect(page.getByRole("navigation", { name: "Officer navigation" })
          .getByRole("link", { name: route.current, exact: true }))
          .toHaveAttribute("aria-current", "page");
      }
    });
  }

  test("profile menu is keyboard operable and returns focus on Escape", async ({ page }) => {
    await page.goto("./");
    const trigger = page.getByRole("button", { name: "Officer Casey Morgan" });
    await trigger.focus();
    await trigger.press("ArrowDown");
    const menu = page.getByRole("menu", { name: "Profile and session" });
    await expect(menu).toBeVisible();
    await expect(menu.getByRole("menuitem").first()).toBeFocused();
    await expectFocusIndicatorUnclipped(menu.getByRole("menuitem").first());
    await menu.getByRole("menuitem").first().press("ArrowDown");
    await expect(menu.getByRole("menuitem").nth(1)).toBeFocused();
    await menu.press("Escape");
    await expect(menu).toHaveCount(0);
    await expect(trigger).toBeFocused();
  });

  test("mobile drawer follows a logical keyboard order and restores focus", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("./");
    const trigger = page.getByRole("button", { name: "Open navigation menu" });
    await trigger.focus();
    await trigger.press("Enter");
    await page.locator(".gow-sidebar").evaluate(async (sidebar) => {
      await Promise.all(sidebar.getAnimations().map((animation) => animation.finished));
    });

    const close = page.getByRole("button", { name: "Close navigation menu" });
    await expect(close).toBeFocused();
    await expectFocusIndicatorUnclipped(close);
    await close.press("Tab");
    const home = page.getByRole("navigation", { name: "Officer navigation" })
      .getByRole("link", { name: "Home", exact: true });
    await expect(home).toBeFocused();
    await expectFocusIndicatorUnclipped(home);
    await home.press("Escape");
    await expect(trigger).toBeFocused();
  });

  test("Home load error exposes keyboard-reachable recovery", async ({ page }) => {
    // React StrictMode starts the initial effect twice in the E2E dev server.
    officerApiState.homeFailuresRemaining = 2;
    await page.goto("./");

    const alert = page.getByRole("alert");
    await expect(alert).toBeVisible();
    const retry = alert.getByRole("button", { name: "Try again" });
    await retry.focus();
    await expect(retry).toBeFocused();
    await retry.press("Enter");
    await expect(page.getByRole("region", { name: "Primary actions" })).toBeVisible();
  });

  test("reduced-data media removes nonessential Home scenery", async ({ page }) => {
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("Emulation.setEmulatedMedia", {
      features: [{ name: "prefers-reduced-data", value: "reduce" }],
    });
    const supportsReducedDataEmulation = await page.evaluate(
      () => matchMedia("(prefers-reduced-data: reduce)").matches,
    );
    test.skip(
      !supportsReducedDataEmulation,
      "This Chromium build does not expose prefers-reduced-data through CDP emulation.",
    );
    await page.goto("./");

    await expect(page.locator(".gow-sidebar-mountain-scene")).toHaveCSS("display", "none");
    const heroBackground = await page.locator(".officer-home-hero").evaluate((hero) => getComputedStyle(hero).backgroundImage);
    expect(heroBackground).not.toContain("url(");
    expect(heroBackground).toContain("linear-gradient");
  });
});

test.describe("administrator route accessibility smoke", () => {
  test.beforeEach(async ({ page }) => { await installAdminApi(page); });

  test("administrator confirmation controls are keyboard reachable", async ({ page }) => {
    await page.goto("./admin/overview");
    const confirmation = page.getByRole("region", { name: "Administrator confirmation" });
    await expect(confirmation).toBeVisible();
    const pin = confirmation.getByLabel("Administrator PIN");
    await pin.focus();
    await expect(pin).toBeFocused();
    await pin.fill("A12345");
    await pin.press("Tab");
    await expect(confirmation.getByRole("button", { name: "Enter Admin Center" })).toBeFocused();
  });

  for (const route of ADMIN_ROUTES) {
    test(`${route.heading} exposes a stable accessible administrator structure`, async ({ page }) => {
      await enterAdmin(page);
      await page.goto(route.path);
      await expectPageStructure(page, route.heading);
      const adminNavigation = page.getByRole("navigation", { name: "Administration navigation" });
      await expect(adminNavigation).toHaveCount(1);
      await expect(adminNavigation.getByRole("link", { name: route.current, exact: true }))
        .toHaveAttribute("aria-current", "page");
    });
  }

  test("administrator step-up dialog has a keyboard-reachable cancel path", async ({ page }) => {
    await page.goto("./admin/review-lab");
    await page.getByLabel("Administrator PIN").fill("A12345");
    await page.getByRole("button", { name: "Enter Admin Center" }).click();
    const launch = page.getByRole("button", { name: /Open Review Lab/ });
    await launch.focus();
    await launch.press("Enter");

    const dialog = page.getByRole("dialog", { name: "Confirm Review Lab launch" });
    await expect(dialog).toBeVisible();
    await page.keyboard.press("Tab");
    const pin = dialog.getByLabel("Administrator PIN");
    await expect(pin).toBeFocused();
    await expectFocusIndicatorUnclipped(pin);
    await pin.fill("A12345");
    await pin.press("Tab");
    const cancel = dialog.getByRole("button", { name: "Cancel" });
    await expect(cancel).toBeFocused();
    await expectFocusIndicatorUnclipped(cancel);
    await cancel.press("Enter");
    await expect(dialog).toHaveCount(0);
  });

  test("status meaning remains readable with achromatopsia emulation", async ({ page }) => {
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("Emulation.setEmulatedVisionDeficiency", { type: "achromatopsia" });
    await enterAdmin(page);

    const statuses = page.locator(".admin-status-mark");
    await expect(statuses.filter({ hasText: "Operational" }).first()).toBeVisible();
    await expect(statuses.filter({ hasText: "Unavailable" }).first()).toBeVisible();
    await expect(statuses.filter({ hasText: "Operational" }).first()).toHaveText("Operational");
    await expect(statuses.filter({ hasText: "Unavailable" }).first()).toHaveText("Unavailable");
  });
});
