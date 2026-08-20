import { describe, expect, it } from "vitest";
import tokens from "../guided-operations.css?raw";

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
});
