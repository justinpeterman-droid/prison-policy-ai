# Guided Operations Visual Asset Register

## 2026-08-20 Home scenery pass

| Asset | Source and method | Privacy review | Delivery |
| --- | --- | --- | --- |
| `operations-horizon-v4.webp` | Edited with Codex built-in Image Gen from the fictional v2 correctional-perimeter scene to extend the continuous fence across the full frame and raise it into the shallow hero crop; resized and WebP-encoded locally. | Fictional scene only. No people, facility name, signs, vehicles, identifiers, or historical records requested or observed. | Home-only hero, Vite-managed import with the CSS gradient as fallback. Includes horizontal crop bleed. 57,254 bytes. |
| `operations-horizon-v4-tablet.webp` | Locally resized derivative of the approved fictional v4 hero; no generative content changes. | Same reviewed fictional scene as the v4 source. | Tablet/standard-desktop Home breakpoint, Vite-managed CSS URL. 24,636 bytes. |
| `operations-horizon-v4-mobile.webp` | Locally resized derivative of the approved fictional v4 hero; no generative content changes. | Same reviewed fictional scene as the v4 source. | Mobile Home breakpoint, Vite-managed CSS URL. 13,660 bytes. |
| `sidebar-mountains-v3.webp` | Edited with Codex built-in Image Gen from the fictional v2 mountain landscape to raise the ridgeline within the portrait composition; resized and WebP-encoded locally. | Fictional landscape only. No people, facility details, signs, or identifiers requested or observed. | Decorative lower navigation rail, Vite-managed import. Solid navy shell remains the layout-safe fallback. 6,350 bytes. |

These assets are decorative (`alt=""`) and must not be used in print output. Production approval remains required before a release that includes generated visual assets.

## Code-native brand and action fixtures

- Retain the existing code-native `BrandShield` for this milestone. Do not introduce a facility crest or photorealistic insignia without a separate owner-approved identity brief.
- The four Home action fixtures remain inline, project-owned SVG components for Incident Report, Count Sheet, Policy Question, and Forms Library. They share one view box, stroke system, material treatment, dimensions, light direction, border, and shadow contract, so they do not add network requests or layout shift.
- Routine interface icons use the separate code-native `InterfaceIcon` family. Decorative action fixtures are never substituted for unlabeled controls.
- The shipped WebP files were checked for common EXIF, XMP, Photoshop, ICC profile, reference-image-name, and identity strings by `visual-assets.test.ts`; no such embedded strings are present. This is a repository integrity check, not a substitute for owner production approval.
