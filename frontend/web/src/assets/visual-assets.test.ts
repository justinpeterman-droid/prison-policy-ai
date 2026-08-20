/// <reference types="node" />

import { readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const assetDirectory = dirname(fileURLToPath(import.meta.url));

function bytes(name: string): number {
  return statSync(join(assetDirectory, name)).size;
}

const PRODUCTION_SCENERY = [
  "operations-horizon-v4.webp",
  "operations-horizon-v4-tablet.webp",
  "operations-horizon-v4-mobile.webp",
  "sidebar-mountains-v3.webp",
] as const;

describe("Guided Operations visual asset budgets", () => {
  it("keeps the Home scenic payload within the narrow-network budget", () => {
    const hero = bytes("operations-horizon-v4.webp");
    const tabletHero = bytes("operations-horizon-v4-tablet.webp");
    const mobileHero = bytes("operations-horizon-v4-mobile.webp");
    const sidebar = bytes("sidebar-mountains-v3.webp");

    expect(hero).toBeLessThanOrEqual(150 * 1024);
    expect(tabletHero).toBeLessThanOrEqual(90 * 1024);
    expect(mobileHero).toBeLessThanOrEqual(60 * 1024);
    expect(sidebar).toBeLessThanOrEqual(30 * 1024);
    expect(hero + sidebar).toBeLessThanOrEqual(180 * 1024);
    expect(mobileHero + sidebar).toBeLessThanOrEqual(90 * 1024);
  });

  it("keeps production scenery free of common embedded metadata and reference artifacts", () => {
    for (const name of PRODUCTION_SCENERY) {
      const content = readFileSync(join(assetDirectory, name)).toString("latin1");
      expect(content).not.toMatch(/EXIF|XMP|Photoshop|ICC_PROFILE|Codex Image|Peterman/i);
    }
  });
});
