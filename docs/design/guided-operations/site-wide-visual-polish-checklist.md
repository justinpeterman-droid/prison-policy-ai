# Guided Operations Site-Wide Visual Polish Checklist

**Reference reviewed:** `Codex Image Aug 20, 2026, 03_06_36 AM.png`

**Status:** implementation checklist

**Primary goal:** make the complete Guided Operations website meet or exceed the reference's refined, high-end visual quality while keeping every officer and administrator workflow clear, fast, and accessible.

## Reference Authority and Data Boundary

The screenshot is the minimum visual-quality and composition target, not merely inspiration for three isolated elements. Its shell proportions, integrated artwork, hierarchy, finish, density, icon treatment, utility rail, panel composition, spacing, and control quality may all be adopted or improved where they support the real product.

Important visual anchors include:

- the privacy-safe prison/watchtower sunrise scene across the top of the Home page;
- the mountain landscape integrated into the lower left navigation rail;
- the dimensional, carefully finished cards, fixtures, icons, and buttons;
- the light, spacious canvas balanced by navy structure and restrained gold accents; and
- the overall sense of a polished operational product that remains easy to use;
- the composed desktop dashboard, utility rail, compact list panels, and bottom trust area;
- the coherent iconography and premium brand treatment; and
- the disciplined alignment, spacing, typography, gradients, borders, and shadows across the entire screen.

The site may look like the full reference or better, but the screenshot does **not** make its sample officer identity, avatar, incident names, counts, dates, notifications, service states, quote, version, checklist entries, links, or other demonstration content true. Production UI must continue to use authorized application data and honest empty states.

## Definition of Success

- [ ] An officer can identify the primary next action within two seconds.
- [ ] The site feels refined and cohesive without looking dark, theatrical, crowded, or game-like.
- [ ] Every primary officer and administrator route—not only Home—looks intentionally designed to the same quality bar.
- [ ] The prison hero and mountain sidebar support hierarchy without obscuring text or navigation.
- [ ] Cards and controls have restrained physical depth, consistent geometry, and obvious interaction states.
- [ ] Existing workflows, authorization boundaries, data integrity, print behavior, and error handling remain intact.
- [ ] Desktop, Windows-scaled, tablet, mobile, keyboard-only, screen-reader, and reduced-motion experiences pass their release checks.
- [ ] No sample or invented operational data is used as a production fallback.

---

## Phase 0 — Protect the Existing Product Before Styling

### Source-of-truth inventory

- [ ] Confirm `App.tsx` remains the active authenticated application shell.
- [ ] Confirm `OfficerHomePage.tsx` remains the production, data-driven Home implementation.
- [ ] Treat `guided-operations.css` and `officer-home.css` as the initial active shell/Home sources while consolidation is in progress.
- [ ] Inventory every stylesheet imported by the active shell and Home route.
- [ ] Identify selectors from `guided-operations.css`, `refinement.css`, `sidebar-scenery.css`, and feature styles that affect the same elements.
- [ ] Inventory import-order overrides in `home-refinement.css` and `styles.css` so the finished appearance does not depend on stylesheet order.
- [ ] Confirm whether `HomePage.tsx`, `OfficerWorkspaceLayout.tsx`, `App.css`, and their related styles are dormant.
- [ ] Record all tests that still import dormant components before removing anything.
- [ ] Remove duplicate shell/Home implementations only after their useful patterns have been migrated and their imports are proven unused.
- [ ] Add a route regression test proving `/` renders the authorized, data-backed Home rather than the static reference component.
- [ ] Keep all existing navigation destinations and route authorization behavior unchanged.

### Baseline capture

- [ ] Capture the current Home page at 1536×1024, 1366×768, 1280×800, 1024×768, 768×1024, and 390×844.
- [ ] Capture the current officer navigation open and closed on tablet/mobile.
- [ ] Capture representative officer pages: New Report, Reports, Document Studio, Policy Expert, Forms Library, Count Sheet, and Account.
- [ ] Capture representative administrator pages: Overview, All Incidents, Paperwork Center, Accounts & Staff, Audit, Health, and Review Lab.
- [ ] Record current keyboard focus order and visible focus treatments.
- [ ] Record current bundle sizes and important route chunk sizes.
- [ ] Run the existing component, typecheck, build, and Playwright gates before visual work begins.

### Non-regression rules

- [ ] Do not replace live incident, form, count-sheet, staff, health, or session data with screenshot examples.
- [ ] Do not change permissions, API payloads, route ownership, persistence, revision, or audit behavior as an incidental styling task.
- [ ] Do not make print layouts inherit screen-only shadows, backgrounds, imagery, or navigation.
- [ ] Do not add new dashboard panels until their data source, authorization, loading, empty, and error behavior are defined.
- [ ] Do not add decorative assets containing real people, real facilities, readable signage, vehicle plates, employee identifiers, or historical records.

### Known baseline defects to correct

- [ ] Increase current 40–42px Home CTA controls to at least 44px where they are primary/touch targets.
- [ ] Replace white text on the current light-gold gradient; measured contrast is approximately 1.90:1 at the light stop and 3.65:1 at the dark stop.
- [ ] Darken or enlarge current muted copy where `#63758A` on `#F4F8FB` measures approximately 4.43:1 and narrowly misses normal-text AA.
- [ ] Strengthen the current semi-transparent focus treatment; its approximate 1.80:1 contrast does not provide a dependable 3:1 component/focus boundary.
- [ ] Disable the Home card's hover translation itself in reduced-motion mode instead of only removing its transition duration.
- [ ] Preserve the current scenic SVGs' very small transfer-size baseline when replacing their generic artwork with higher-fidelity assets.

---

## Phase 1 — Establish the Shared Visual System

### Color tokens

- [ ] Define one canonical token file for canvas, surface, raised surface, inset surface, borders, text, muted text, navy, blue, gold, success, warning, danger, neutral, focus, and disabled colors.
- [ ] Keep the visual balance near 80% light surfaces, 15% navy structure, and 5% gold/semantic accents.
- [ ] Use navy for structure, navigation, headings, and high-confidence secondary actions.
- [ ] Reserve gold for the selected navigation item, the single primary action in a context, and small premium accents.
- [ ] Avoid using gold for large text blocks, routine metadata, or every interactive control.
- [ ] Use dark navy text on light gold where white text does not meet contrast.
- [ ] Test every text/background combination instead of assuming gradients pass contrast.
- [ ] Define semantic colors independently from decorative gold/blue so status meaning never depends on branding color.

### CSS consolidation

- [ ] Consolidate active shell styling into one maintained shell stylesheet.
- [ ] Consolidate active Home styling into `officer-home.css` or an equally explicit feature-owned module.
- [ ] Move active sidebar scenery rules into the maintained shell layer.
- [ ] Split genuinely administrator-specific refinements away from global officer styles.
- [ ] Remove duplicate hero, action-card, button, sidebar, and status selectors after visual parity is confirmed.
- [ ] Replace separate `--gow-*`, `--admin-*`, Count Sheet, and dormant prototype color values with shared semantic tokens plus necessary feature aliases.
- [ ] Remove the stale `assets/sidebar-mountains.jpg` reference after confirming it is not part of the supported build.
- [ ] Keep official paperwork print rules isolated from all decorative screen tokens.
- [ ] Do not make production typography depend on a public font CDN being reachable from the facility network.

### Typography

- [ ] Use one highly legible sans-serif stack for navigation, controls, forms, tables, and body copy.
- [ ] Define tokens for display heading, page heading, panel heading, body, supporting copy, label, metadata, and compact table text.
- [ ] Keep body text at least 16 CSS pixels on mobile and avoid dense desktop text below 12 CSS pixels.
- [ ] Use a display serif only for a small brand or quotation treatment if it remains legible and does not spread into operational UI.
- [ ] Tighten large Home greeting typography without clipping long names or browser zoom.
- [ ] Prevent all-caps tracking from reducing readability in small labels.
- [ ] Use tabular numerals where aligned counts, dates, times, or incident numbers benefit from them.

### Spacing, radii, borders, and elevation

- [ ] Define a spacing scale and remove one-off gaps that create uneven density.
- [ ] Define small, medium, and large surface radii; avoid a different radius on every component.
- [ ] Define separate border tokens for standard, strong, focus, warning, and destructive states.
- [ ] Define three elevation levels: control, card, and feature fixture.
- [ ] Keep data tables and dense editors mostly flat for scanning performance.
- [ ] Use deeper elevation only for primary action fixtures, active navigation, print stacks, and important dialogs.
- [ ] Ensure shadows remain visible but subtle on common Windows displays.
- [ ] Remove double shadows and nested raised surfaces that make the interface look inflated.

### Icon system

- [ ] Select one coherent SVG icon family for navigation and routine actions.
- [ ] Standardize stroke/fill weight, optical size, alignment, corner style, and active-state treatment.
- [ ] Replace text glyphs such as `›`, `→`, `◇`, `▤`, and `⌄` in functional controls with accessible SVG icons.
- [ ] Keep decorative fixture artwork separate from the routine interface icon family.
- [ ] Ensure icon-only controls have accessible names and visible tooltips where meaning is not obvious.
- [ ] Mark purely decorative icons and artwork as hidden from assistive technology.

### Motion

- [ ] Define 120–180ms control feedback and 180–240ms navigation/panel transitions.
- [ ] Limit movement to small position changes, shadow compression, opacity, and active-state transitions.
- [ ] Give raised buttons approximately 2px of pressed travel with a compressed contact shadow.
- [ ] Avoid delayed entrances, continuous motion, parallax, looping glows, or decorative animation during operational work.
- [ ] Make reduced-motion mode remove travel while preserving immediate state/color feedback.

---

## Phase 2 — Create the Visual Assets

### Top prison/watchtower hero scene

- [ ] Produce a fictional, non-identifying correctional perimeter scene with sunrise light, fence silhouette, and watchtower.
- [ ] Keep the image calm and professional; avoid inmates, weapons, emergency activity, threatening weather, or dramatic surveillance imagery.
- [ ] Compose the brightest and lowest-detail area behind the greeting text.
- [ ] Place the watchtower and fence detail toward the right so they do not compete with the employee name.
- [ ] Include sufficient bleed for wide desktop crops without cutting off the tower.
- [ ] Create alternate crops for wide desktop, standard desktop, tablet, and mobile.
- [ ] Provide AVIF/WebP delivery plus a dependable fallback.
- [ ] Define explicit width, height, and aspect ratio to prevent layout shift.
- [ ] Add a CSS light-edge fade or scrim rather than permanently washing out the source artwork.
- [ ] Verify legibility with short and very long fictional employee names.
- [ ] Verify the asset at normal, high-contrast, forced-colors, and reduced-data conditions.
- [ ] Provide a gradient-only fallback when the image cannot load.
- [ ] Keep hero artwork out of printed pages.

### Left mountain scene

- [ ] Produce or refine a fictional mountain landscape for the lower sidebar.
- [ ] Keep the upper navigation area solid enough to preserve label and icon contrast.
- [ ] Fade the mountain scene into navy before it reaches navigation links.
- [ ] Keep scenic detail strongest near the bottom and progressively quieter upward.
- [ ] Ensure the scene works at the permanent desktop sidebar width and the wider mobile drawer width.
- [ ] Prevent the scenery from intercepting pointer or keyboard interaction.
- [ ] Use optimized dimensions and formats rather than loading a full-screen photograph into a narrow rail.
- [ ] Provide a solid navy fallback with no layout change.
- [ ] Confirm the artwork never appears behind print output.

### Brand crest and feature fixtures

- [ ] Decide whether the current code-native shield remains or an approved fictional crest replaces it.
- [ ] If a crest is added, keep the product name code-native and the crest decorative.
- [ ] Produce four visually related fixtures for Incident Report, Count Sheet, Policy Question, and Forms Library.
- [ ] Use consistent perspective, light direction, material finish, border treatment, and shadow softness across fixtures.
- [ ] Keep fixture dimensions stable so action-card text does not jump while assets load.
- [ ] Avoid photorealistic staff portraits or facility-specific insignia.
- [ ] Verify every generated asset is licensed/approved for repository and production use.
- [ ] Record the source, license, generation method, approval, and privacy review for every scenic or fixture asset.
- [ ] Sanitize SVG assets and reject scripts, remote references, tracking, embedded raster metadata, or unsafe markup.
- [ ] Choose one maintained source for each scene and document how Vite publishes it; do not hand-edit generated backend build output.

---

## Phase 3 — Refine the Application Shell

### Desktop sidebar

- [ ] Preserve exactly Home, New Report, Reports, Policy Expert, Forms Library, and Account for officers.
- [ ] Keep the Administration entry role-gated and visually separated without creating a second competing navigation system.
- [ ] Rebuild the brand block with a controlled curved or angled lower-right edge inspired by the reference.
- [ ] Keep the gold separator crisp and restrained.
- [ ] Integrate the mountain scene into the lower rail without placing text over high-detail terrain.
- [ ] Standardize nav-row height, horizontal padding, icon box, label baseline, and vertical gap.
- [ ] Make the active nav item unmistakable through shape, color, and position—not color alone.
- [ ] Expose the active destination with `aria-current="page"`.
- [ ] Give hover, focus, pressed, and active states distinct treatments.
- [ ] Keep every nav target at least 44×44 CSS pixels.
- [ ] Remove detailed service health from the sidebar.
- [ ] Keep only a compact brand tagline or safe session note at the bottom.
- [ ] Show a version only when sourced from real build metadata.
- [ ] Verify sidebar scrolling does not hide primary navigation at 768px-tall displays.

### Top utility bar

- [ ] Visually integrate the top utility controls with the hero edge on Home.
- [ ] Use a simpler neutral topbar on working pages so it does not reduce editor/document space.
- [ ] Separate network connectivity, last successful refresh, and backend service health.
- [ ] Show `Online`, `Reconnecting`, or `Offline` only from actual connectivity state.
- [ ] Show last refreshed/synced time only from a trustworthy timestamp.
- [ ] Add notifications only when backed by an actionable, authorized source.
- [ ] Provide an honest zero-notification state.
- [ ] Convert the profile chip into a real button with `aria-expanded` and keyboard-operated menu behavior.
- [ ] Include Account, role/shift context, session status, and Sign Out in the menu.
- [ ] Use initials as the default privacy-safe identity treatment.
- [ ] Add an avatar only after defining an approved source, storage, fallback, and revocation behavior.

### Main workspace frame

- [ ] Add a centered maximum-width content container for Home so ultrawide screens do not create a large empty field.
- [ ] Use disciplined left/right gutters aligned with the hero and card grid.
- [ ] Keep report, form, table, and editor routes able to use wider working space than Home.
- [ ] Avoid applying a permanent Home utility rail to Document Studio, Count Sheet, Paperwork Center, or other dense workspaces.
- [ ] Preserve a predictable page-header location on every non-Home route.

---

## Phase 4 — Refine the Officer Home Page

### Hero

- [ ] Use the prison/watchtower scene only on Home, not as a banner repeated on every route.
- [ ] Render the signed-in employee’s real authorized display name dynamically.
- [ ] Keep greeting time-of-day logic accurate or use a neutral greeting when client time is unreliable.
- [ ] Decide whether shift belongs in the hero or profile menu; avoid repeating it in both at equal emphasis.
- [ ] Keep the supporting message short, calm, and approved.
- [ ] Preserve Professionalism, Accountability, and Integrity as secondary detail rather than primary navigation.
- [ ] Ensure the hero remains useful when the image fails or the user increases text size to 200%.

### Primary action cards

- [ ] Keep exactly four primary action cards: New Incident Report, Count Sheet, Policy Question, and Forms Library.
- [ ] Remove decorative `01`–`04` watermark numbers.
- [ ] Use one fixture, one heading, one short supporting sentence, and one clear action per card.
- [ ] Keep action labels concise: Start, Open, Ask, and Browse.
- [ ] Preserve existing routes and accessible link names.
- [ ] Keep only the highest-priority action gold; use refined navy/blue for the other actions.
- [ ] Align fixture size, heading position, body-copy height, and button baseline across all four cards.
- [ ] Prevent fixed text heights from clipping translated, zoomed, or longer copy.
- [ ] Make the whole card feel cohesive without turning the whole surface into an ambiguous click target.
- [ ] Add loading and disabled states only where the action genuinely has asynchronous availability.
- [ ] Surface today’s Count Sheet state compactly in its card when available.

### Card finish

- [ ] Use a quiet white-to-cool-white surface gradient.
- [ ] Add one fine border, one subtle top highlight, and one restrained contact shadow.
- [ ] Avoid glass blur on every card; reserve transparency for the shell/topbar if needed.
- [ ] Keep card content contrast independent of background artwork.
- [ ] Use consistent internal padding and vertical rhythm.
- [ ] Use hover elevation only on interactive cards and disable travel for reduced motion.
- [ ] Keep static information panels visually quieter than action cards.

### Continue, incidents, and forms

- [ ] Restyle Continue Your Work as the strongest data panel below the actions.
- [ ] Keep incident number first, incident name second, progress state, updated time, and one Continue action.
- [ ] Remove decorative metrics that do not help the officer decide what to do next.
- [ ] Make Recent Incidents rows fully clickable with clear focus and hover states.
- [ ] Preserve computed workflow progress; do not copy sample status labels from the reference.
- [ ] Keep relative times paired with machine-readable timestamps where applicable.
- [ ] Call forms `Frequently Used` only if ranking is real; otherwise use `Quick Forms` or `Common Forms`.
- [ ] Show print actions only for forms whose capability permits printing.
- [ ] Preserve physical-only guidance instead of presenting a fake digital form.

### Desktop utility rail

- [ ] Implement the right utility rail on wide Home layouts where it does not compress the primary cards.
- [ ] Limit the initial rail to Quick Access, summarized System Status, and Help.
- [ ] Build Quick Access from existing valid destinations.
- [ ] Give Daily Paperwork a real authorized destination before exposing it as a shortcut.
- [ ] Keep service health summarized as Operational, Degraded, Unavailable, or Unknown.
- [ ] Do not reveal database hosts, model configuration, credentials, raw exceptions, or infrastructure topology.
- [ ] Point Help to a real approved destination; omit the panel until one exists.
- [ ] Move the rail below primary content at medium desktop widths.
- [ ] Do not hide rail functions on mobile; relocate essential shortcuts into the content flow.

### Lower-priority panels

- [ ] Add a daily checklist only after its date, shift, role, ownership, and completion semantics are defined.
- [ ] Treat checklist circles as status indicators unless the officer is explicitly permitted to change completion.
- [ ] Add recent activity only from safe, personal, authorization-scoped event summaries.
- [ ] Exclude narratives, form values, policy prompts, credentials, raw audit payloads, and other employees’ activity.
- [ ] Avoid repeating the same destination in primary actions, Quick Access, Quick Links, and Help unless usage testing proves the redundancy useful.
- [ ] Keep any quote/trust strip visually subordinate and remove it on narrower layouts if it adds noise.
- [ ] Use locale-aware date/time only if it helps the task; do not create a constantly updating decorative clock.

---

## Phase 5 — Refine Cards and Buttons Site-Wide

### Button system

- [ ] Create canonical primary, secondary, destructive, quiet/text, icon-only, and segmented-control variants.
- [ ] Use a refined gold primary treatment only for the dominant action.
- [ ] Use a navy/blue raised treatment for normal affirmative actions.
- [ ] Keep destructive actions red and visually separate from brand gold.
- [ ] Include top highlight, darker lower edge, restrained shadow, and approximately 2px active travel.
- [ ] Define hover, focus-visible, active, loading, disabled, and selected states for every variant.
- [ ] Keep button text and icons centered at all supported zoom levels.
- [ ] Keep minimum height at 44px for primary/mobile controls and adequate width for comfortable targeting.
- [ ] Prefer 48px height for the four major officer actions and keep at least 8px between adjacent touch targets.
- [ ] Never rely on shadow alone to communicate disabled or selected state.
- [ ] Apply hover-only elevation inside `@media (hover: hover)` so touch devices do not retain misleading hover states.

### Shared cards and panels

- [ ] Create reusable surface variants for action card, information panel, list panel, inset row, empty state, warning, and dialog.
- [ ] Standardize header spacing, heading hierarchy, optional action placement, and body padding.
- [ ] Use one list-row pattern for chevron navigation and another explicit pattern for actions such as Print or Open.
- [ ] Keep status chips semantically consistent across Home, Reports, Document Studio, Administration, and Paperwork Center.
- [ ] Avoid nested card-within-card-within-card layouts.
- [ ] Keep admin density higher through spacing and information layout, not by abandoning the visual system.

### Form and data controls

- [ ] Standardize input, select, textarea, search, checkbox, radio, switch, date, and time controls.
- [ ] Define normal, hover, focus, populated, disabled, read-only, invalid, and successful states.
- [ ] Keep labels visible; do not use placeholder text as the only label.
- [ ] Keep required/optional and validation language consistent.
- [ ] Preserve dense table scanning and keyboard entry in operational paperwork editors.
- [ ] Keep sticky headers and horizontal scrolling deliberate on narrow data views.

---

## Phase 6 — Apply the System Page by Page

### Officer routes

- [ ] Home: complete the hero, primary actions, core panels, and optional utility rail.
- [ ] New Report: clarify the single next step and keep AI/data provenance visible.
- [ ] Reports: refine search, filters, incident rows, status chips, loading, and empty states.
- [ ] Document Studio: preserve maximum writing/review space and keep decorative depth minimal.
- [ ] Policy Expert: refine question entry, citations, source cards, and answer confidence without making AI look infallible.
- [ ] Forms Library: refine category/search controls, capability labels, physical-only guidance, and print actions.
- [ ] Count Sheet: preserve keypad/table efficiency while applying shared controls and surface tokens.
- [ ] Account: refine identity, session, PIN, sign-out, and security states without unnecessary decoration.

### Administrator routes

- [ ] Overview: use the shared system with denser information hierarchy and clear exceptions.
- [ ] All Incidents: standardize filters, attributed rows, status chips, and admin actions.
- [ ] Paperwork Center: preserve working width and print behavior while standardizing tabs, cards, forms, and save states.
- [ ] Accounts & Staff: standardize sensitive actions, step-up prompts, temporary PIN presentation, and session controls.
- [ ] Audit: prioritize scanability and redaction over dimensional decoration.
- [ ] Health: use semantic status hierarchy without exposing unsafe infrastructure details.
- [ ] Review Lab: preserve its approved operational workflow and handoff safeguards.

### Shared states

- [ ] Provide refined skeletons that match final geometry.
- [ ] Provide honest empty states with a useful next action when one exists.
- [ ] Provide reconnecting/offline states that distinguish local input preservation from server persistence.
- [ ] Standardize unsaved, saving, saved, conflict, failed, and retry states.
- [ ] Standardize warning, destructive confirmation, success, and dependency-unavailable messaging.
- [ ] Keep error recovery controls keyboard reachable and descriptive.

---

## Phase 7 — Responsive and Windows Usability

### Wide and standard desktop

- [ ] Match the intended visual quality at approximately 1536×1024 without copying demonstration data.
- [ ] Verify 1366×768 without clipped buttons, hidden panel actions, inaccessible sidebar items, or excessive empty canvas.
- [ ] Verify 1280×720 and other short-height laptop layouts without shrinking controls below usable sizes.
- [ ] Keep the utility rail only when the remaining main column is comfortably readable.
- [ ] Switch four action cards to a 2×2 layout before labels become compressed.
- [ ] Verify Windows display scaling at 100%, 125%, and 150%.
- [ ] Verify browser zoom at 80%, 100%, 125%, 150%, 200%, and 400% where WCAG reflow applies.

### Tablet

- [ ] Convert the permanent sidebar to an accessible drawer or compact rail.
- [ ] Preserve the hero greeting and immediately useful actions without oversized artwork.
- [ ] Use purpose-built two-column/one-column panel ordering.
- [ ] Keep drawers dismissible by close button, scrim, and Escape.
- [ ] Restore focus to the menu trigger after closing.

### Mobile

- [ ] Verify approximately 390×844 and 360×800 layouts.
- [ ] Verify 430×932, 320×568, and approximately 844×390 mobile landscape layouts.
- [ ] Use a one-column action stack with concise descriptions.
- [ ] Keep Count Sheet, New Report, Reports, Policy Expert, Forms, and Account immediately reachable.
- [ ] Prevent horizontal page overflow.
- [ ] Allow tables to use a labeled, contained horizontal-scroll region where unavoidable.
- [ ] Avoid hiding operational status, error recovery, checklist, or support solely to simplify the screen.
- [ ] Keep fixed/sticky elements from covering form controls when the on-screen keyboard opens.
- [ ] Respect safe-area insets for mobile navigation and bottom controls.
- [ ] Prevent background scrolling while the navigation drawer is open.

---

## Phase 8 — Accessibility Acceptance

- [ ] Meet WCAG 2.2 AA contrast for text, icons, borders needed for understanding, focus indicators, and control states.
- [ ] Test gold buttons in every gradient position; use navy text or a darker gold when white fails.
- [ ] Meet 44×44 CSS pixel target guidance for primary and touch interactions.
- [ ] Provide visible `:focus-visible` states that are not clipped by overflow or shadows.
- [ ] Verify logical keyboard order through sidebar, utility bar, hero actions, panels, menus, drawers, and dialogs.
- [ ] Verify Enter/Space activation and Escape dismissal where expected.
- [ ] Give menus, notifications, disclosure controls, and dialogs correct names, states, and relationships.
- [ ] Announce save, reconnect, validation, loading completion, and recoverable error states appropriately.
- [ ] Keep artwork decorative unless it conveys information unavailable in text.
- [ ] Verify text resizing to 200% without clipping or loss of controls.
- [ ] Verify 400% zoom/reflow for appropriate non-document pages.
- [ ] Test with forced colors/high contrast and ensure selected/active/status states remain understandable.
- [ ] Test reduced motion and confirm no required information depends on animation.
- [ ] Test screen-reader navigation landmarks and heading order on every primary route.

---

## Phase 9 — Performance and Production Integrity

- [ ] Set route-specific budgets for Home JavaScript, CSS, and visual assets.
- [ ] Keep combined initial scenic imagery near or below 350KB on desktop and 180KB on mobile unless measured evidence supports a larger budget.
- [ ] Keep large decorative assets out of non-Home route chunks.
- [ ] Preload only the Home hero image that materially improves first render.
- [ ] Lazy-load below-the-fold illustrations and noncritical fixtures.
- [ ] Use responsive image sources and avoid serving the 1536px reference crop to a narrow phone.
- [ ] Treat a raster/photo hero as the Home LCP asset: load it early and do not lazy-load it.
- [ ] Ensure image failure never removes navigation, labels, or actions.
- [ ] Verify no layout shift when hero, sidebar, crest, or fixtures load.
- [ ] Confirm Vite-hashed assets receive immutable caching and the SPA document remains `no-store`.
- [ ] Confirm Content Security Policy permits the selected same-origin asset strategy without unsafe inline scripts.
- [ ] Confirm production images contain no source reference screenshot, uploaded design drafts, real identities, or unintended metadata.
- [ ] Verify scenic assets load from the production static path in the Cloud Run image.
- [ ] Meet production p75 goals of LCP ≤2.5s, CLS ≤0.1, and INP ≤200ms.

---

## Phase 10 — Visual Regression and Release Gate

### Automated coverage

- [ ] Add stable fictional Home fixtures for populated, loading, empty, error, reconnecting, and reduced-motion states.
- [ ] Add desktop screenshots at 1536×1024 and 1366×768.
- [ ] Add Windows-scaled or equivalent browser-zoom screenshots for 125% and 150% review.
- [ ] Add tablet screenshots in portrait and landscape.
- [ ] Add mobile screenshots at 390×844 and 360×800.
- [ ] Add 430×932, 320×568, and mobile-landscape references for edge-case review.
- [ ] Add sidebar/drawer open, profile menu open, notification state, keyboard focus, and error-state references.
- [ ] Add forced-colors references or assertions for navigation, cards, buttons, status, and focus.
- [ ] Add representative screenshots for every officer and administrator route after shared-token migration.
- [ ] Mask or use fictional data in every screenshot, video, trace, and report.
- [ ] Keep print screenshots separate and verify screen decoration does not enter print output.

### Manual visual review

- [ ] Compare hero crop, text-safe area, watchtower placement, sidebar fade, card density, button depth, icons, spacing, and alignment against the approved visual cues.
- [ ] Confirm the result feels polished without copying every panel or piece of demonstration content from the reference.
- [ ] Confirm the visual hierarchy remains obvious during real loading, empty, error, and incomplete-data states.
- [ ] Check common Windows laptop displays for muddy shadows, low-contrast borders, and overly small metadata.
- [ ] Check grayscale readability for status and print-related screens.
- [ ] Record every intentional deviation with a usability, accessibility, security, performance, or data-integrity reason.

### Required verification

- [ ] Run frontend component tests.
- [ ] Run TypeScript checking.
- [ ] Run the production frontend build and review bundle output.
- [ ] Run officer Playwright workflows.
- [ ] Run administrator Playwright workflows.
- [ ] Run desktop, tablet, mobile, keyboard, and reduced-motion paths.
- [ ] Run automated accessibility checks and complete a manual keyboard/screen-reader pass.
- [ ] Review failed-test screenshots, videos, and traces before accepting updates.
- [ ] Verify the complete print suite after every shared CSS change.
- [ ] Require all CI and release gates to pass before merging each visual milestone.

---

## Recommended Delivery Milestones

### Milestone V1 — Foundation and shell

- [ ] Reconcile active/dormant frontend implementations.
- [ ] Establish tokens, icon family, button system, card system, focus, and motion.
- [ ] Implement the mountain sidebar and shell refinements.
- [ ] Verify all existing routes before moving forward.

### Milestone V2 — Home visual transformation

- [ ] Implement the prison/watchtower hero.
- [ ] Implement four refined primary action cards and fixtures.
- [ ] Restyle Continue Your Work, Recent Incidents, Quick Forms, and Count Sheet status using existing data.
- [ ] Complete Home responsive and accessibility checks.

### Milestone V3 — Data-backed utilities

- [ ] Add Quick Access from existing routes.
- [ ] Add safe summarized System Status only after its contract is approved.
- [ ] Add Help only with a real destination.
- [ ] Add notifications, daily checklist, and activity only after each data contract and authorization rule is approved.

### Milestone V4 — Site-wide propagation

- [ ] Apply shared tokens and components across all officer routes.
- [ ] Apply the same system at administrator density across all admin routes.
- [ ] Preserve Document Studio, paperwork editing, and print working space.

### Milestone V5 — Formal acceptance

- [ ] Complete all responsive, accessibility, performance, visual-regression, and print gates.
- [ ] Complete owner review using the actual application with fictional data.
- [ ] Resolve every material, fixable mismatch.
- [ ] Mark Site-Wide Visual Polish complete only after the production build—not a static mockup—meets the agreed quality bar.
