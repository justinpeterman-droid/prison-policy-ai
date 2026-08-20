# Guided Operations Visual Performance Budget

## Initial route budgets

These budgets apply to the production Vite build and are release ceilings, not targets to consume.

| Route class | JavaScript (gzip) | CSS (gzip) | Scenic imagery transferred |
| --- | ---: | ---: | ---: |
| Officer Home | 150 KB | 35 KB | 180 KB maximum |
| Officer working routes | 150 KB | 35 KB | Sidebar scene only, 30 KB maximum |
| Administrator working routes | 150 KB | 35 KB | No Home hero transfer |

The broader checklist permits up to 350 KB of combined initial scenic imagery on desktop. This project uses the stricter 180 KB mobile ceiling for every Home load because facility connectivity may be constrained.

## Maintained assets

- `operations-horizon-v4.webp`: Home-only CSS background; 57,254 bytes.
- `operations-horizon-v4-tablet.webp`: responsive Home derivative; 24,636 bytes.
- `operations-horizon-v4-mobile.webp`: responsive Home derivative; 13,660 bytes.
- `sidebar-mountains-v3.webp`: shell decoration; 6,350 bytes.
- Combined scenic payload: 63,604 bytes.

`visual-assets.test.ts` enforces the individual and combined image ceilings. Production build review must also confirm that non-Home elements never reference the Home hero, hashed assets retain immutable caching, and the SPA document remains `no-store`.

## Loading and resilience contract

- Home mounts three media-qualified `<link rel="preload" as="image" type="image/webp">` candidates. Only the candidate matching the active desktop, tablet, or mobile media query is fetched at high priority, and all three preload elements are removed when Home unmounts.
- The 6.35KB sidebar landscape is explicitly dimensioned, asynchronously decoded, low priority, and lazy loaded. Its absolute positioning and solid-navy shell fallback prevent it from shifting navigation.
- Hero geometry is reserved by CSS before imagery arrives. Browser coverage records a layout-shift score at or below `0.1` and proves that aborting every WebP request leaves the authorized name, navigation, and four primary actions operable.
- `prefers-reduced-data: reduce` removes both decorative scenes while preserving the light hero surface and solid navy navigation shell.
- Print media removes scenic imagery and screen-only shell decoration.

The current application is delivered as one initial JavaScript and CSS bundle. Route splitting is a future optimization trigger if either compressed bundle exceeds its ceiling; it is not a reason to defer the image budget or caching checks.
