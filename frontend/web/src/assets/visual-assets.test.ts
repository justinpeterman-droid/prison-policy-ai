/// <reference types="node" />

import { readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const assetDirectory = dirname(fileURLToPath(import.meta.url));

function bytes(name: string): number {
  return statSync(join(assetDirectory, name)).size;
}

function webpDimensions(name: string): { width: number; height: number } {
  const image = readFileSync(join(assetDirectory, name));
  expect(image.toString("ascii", 0, 4)).toBe("RIFF");
  expect(image.toString("ascii", 8, 12)).toBe("WEBP");
  const chunk = image.toString("ascii", 12, 16);

  if (chunk === "VP8X") {
    return {
      width: image.readUIntLE(24, 3) + 1,
      height: image.readUIntLE(27, 3) + 1,
    };
  }
  if (chunk === "VP8L") {
    const bits = image.readUInt32LE(21);
    return {
      width: (bits & 0x3fff) + 1,
      height: ((bits >>> 14) & 0x3fff) + 1,
    };
  }
  if (chunk === "VP8 ") {
    return {
      width: image.readUInt16LE(26) & 0x3fff,
      height: image.readUInt16LE(28) & 0x3fff,
    };
  }
  throw new Error(`Unsupported WebP chunk ${chunk} in ${name}`);
}

const PRODUCTION_SCENERY = [
  "operations-horizon-v4.webp",
  "operations-horizon-v4-tablet.webp",
  "operations-horizon-v4-mobile.webp",
  "sidebar-mountains-v3.webp",
] as const;

const ACTIVE_INLINE_ARTWORK = [
  join(assetDirectory, "..", "App.tsx"),
  join(assetDirectory, "..", "components", "InterfaceIcon.tsx"),
  join(assetDirectory, "..", "features", "dashboard", "OfficerHomePage.tsx"),
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

  it("keeps explicit intrinsic dimensions for every responsive scenery asset", () => {
    expect(webpDimensions("operations-horizon-v4.webp")).toEqual({ width: 1536, height: 640 });
    expect(webpDimensions("operations-horizon-v4-tablet.webp")).toEqual({ width: 1024, height: 426 });
    expect(webpDimensions("operations-horizon-v4-mobile.webp")).toEqual({ width: 768, height: 320 });
    expect(webpDimensions("sidebar-mountains-v3.webp")).toEqual({ width: 480, height: 1016 });
  });

  it("keeps production scenery free of common embedded metadata and reference artifacts", () => {
    for (const name of PRODUCTION_SCENERY) {
      const content = readFileSync(join(assetDirectory, name)).toString("latin1");
      expect(content).not.toMatch(/EXIF|XMP|Photoshop|ICC_PROFILE|Codex Image|Peterman/i);
    }
  });

  it("keeps active inline SVG artwork free of executable or remote content", () => {
    for (const path of ACTIVE_INLINE_ARTWORK) {
      const source = readFileSync(path, "utf8");
      const inlineSvgs = [...source.matchAll(/<svg\b[\s\S]*?<\/svg>/gi)].map(([svg]) => svg);
      expect(inlineSvgs.length).toBeGreaterThan(0);
      for (const svg of inlineSvgs) {
        expect(svg).not.toMatch(/<script\b|<foreignObject\b|\bon\w+\s*=|(?:href|src)\s*=\s*["'](?:https?:)?\/\//i);
        expect(svg).not.toMatch(/data:(?:text\/html|image\/svg\+xml)/i);
      }
    }
  });

  it("keeps reduced-data scenery fallbacks explicit and request-free", () => {
    const shellCss = readFileSync(join(assetDirectory, "..", "guided-operations.css"), "utf8");
    const homeCss = readFileSync(
      join(assetDirectory, "..", "features", "dashboard", "officer-home.css"),
      "utf8",
    );

    expect(shellCss).toMatch(
      /@media\s*\(prefers-reduced-data:\s*reduce\)[\s\S]*?\.gow-sidebar-mountain-scene\s*{\s*display:\s*none;/,
    );
    const homeFallback = homeCss.match(
      /@media\s*\(prefers-reduced-data:\s*reduce\)\s*{([\s\S]*?)\n}/,
    )?.[1];
    expect(homeFallback).toContain(".officer-home-hero");
    expect(homeFallback).toContain("background-image: linear-gradient");
    expect(homeFallback).not.toContain("url(");
  });
});
