import { describe, expect, it } from "vitest";
import tokens from "../guided-operations.css?raw";
import adminStyles from "../features/administration/admin.css?raw";
import countSheetStyles from "../features/paperwork/count-sheet/count-sheet.css?raw";

function token(name: string): string {
  const match = tokens.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!match) throw new Error(`Missing color token --${name}`);
  return match[1];
}

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((index) => Number.parseInt(hex.slice(index, index + 2), 16) / 255);
  const linear = channels.map((channel) => (
    channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
  ));
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

function contrast(foreground: string, background: string): number {
  const first = luminance(foreground);
  const second = luminance(background);
  return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
}

describe("Guided Operations contrast contracts", () => {
  it("publishes the canonical typography, spacing, radius, border, and elevation contract", () => {
    for (const name of [
      "gow-font-sans",
      "gow-type-display",
      "gow-type-body",
      "gow-type-supporting",
      "gow-type-control",
      "gow-space-1",
      "gow-space-4",
      "gow-space-8",
      "gow-radius-control",
      "gow-radius-card",
      "gow-radius-feature",
      "gow-border-standard-rule",
      "gow-border-warning-rule",
      "gow-border-danger-rule",
      "gow-elevation-control",
      "gow-elevation-card",
      "gow-elevation-fixture",
    ]) {
      expect(tokens).toContain(`--${name}:`);
    }
  });

  it("keeps active feature aliases connected to the shared semantic contract", () => {
    for (const [alias, shared] of [
      ["admin-navy", "gow-navy-900"],
      ["admin-gold", "gow-gold-700"],
      ["admin-canvas", "gow-canvas"],
      ["admin-text", "gow-ink"],
      ["admin-success", "gow-success"],
      ["admin-warning", "gow-warning"],
      ["admin-danger", "gow-danger"],
      ["admin-focus", "gow-focus"],
    ]) {
      expect(adminStyles).toMatch(new RegExp(`--${alias}:\\s*var\\(--${shared},`));
    }
    for (const [alias, shared] of [
      ["count-navy", "gow-navy-900"],
      ["count-navy-2", "gow-navy-800"],
      ["count-gold", "gow-gold-500"],
      ["count-line", "gow-border"],
      ["count-paper", "gow-surface"],
    ]) {
      expect(countSheetStyles).toMatch(new RegExp(`--${alias}:\\s*var\\(--${shared},`));
    }
  });

  it("publishes canonical interaction, surface, button, and form-state contracts", () => {
    for (const name of [
      "gow-border-focus-rule",
      "gow-focus-offset",
      "gow-duration-feedback",
      "gow-duration-control",
      "gow-duration-panel",
      "gow-duration-navigation",
      "gow-travel-pressed",
      "gow-travel-hover",
      "gow-surface-information",
      "gow-surface-list",
      "gow-surface-inset",
      "gow-surface-empty",
      "gow-surface-warning",
      "gow-surface-dialog",
      "gow-button-primary-background",
      "gow-button-secondary-background",
      "gow-button-destructive-background",
      "gow-button-quiet-background",
      "gow-button-disabled-background",
      "gow-control-height",
      "gow-control-height-major",
      "gow-form-background",
      "gow-form-border",
      "gow-form-border-focus",
      "gow-form-disabled-background",
      "gow-form-readonly-background",
      "gow-form-invalid-border",
      "gow-form-success-border",
    ]) {
      expect(tokens).toContain(`--${name}:`);
    }
  });

  it("keeps gold-button text readable across both gradient stops", () => {
    const ink = token("gow-button-gold-ink");
    expect(contrast(ink, "#e3b64f")).toBeGreaterThanOrEqual(4.5);
    expect(contrast(ink, "#b97814")).toBeGreaterThanOrEqual(4.5);
  });

  it("keeps normal muted copy readable on the light canvas", () => {
    expect(contrast(token("gow-muted"), "#f4f8fb")).toBeGreaterThanOrEqual(4.5);
    expect(contrast(token("gow-muted"), token("gow-surface"))).toBeGreaterThanOrEqual(4.5);
  });

  it("keeps the focus boundary visible on common light surfaces", () => {
    const focus = token("gow-focus");
    expect(contrast(focus, token("gow-canvas"))).toBeGreaterThanOrEqual(3);
    expect(contrast(focus, token("gow-surface"))).toBeGreaterThanOrEqual(3);
  });

  it("keeps rendered semantic status text readable on its active soft surface", () => {
    const activeStatusPairs = [
      [token("gow-success"), token("gow-success-soft")],
      [token("gow-warning"), token("gow-warning-soft")],
      [token("gow-danger"), "#fff0ee"],
      ["#8b5d59", "#f3eeee"],
      ["#52697d", "#edf2f6"],
      ["#52606e", "#eef1f3"],
      ["#5c6670", "#eceef1"],
      ["#7d5413", "#fff2d2"],
      ["#1c5a3d", "#e8f6ed"],
      ["#315f7b", "#eaf4fa"],
    ] as const;

    for (const [foreground, background] of activeStatusPairs) {
      expect(contrast(foreground, background), `${foreground} on ${background}`).toBeGreaterThanOrEqual(4.5);
    }
  });
});
