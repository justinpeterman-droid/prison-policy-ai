# Guided Operations Site-Wide Visual Polish Checklist

**Reference reviewed:** `Codex Image Aug 20, 2026, 03_06_36 AM.png`

**Status:** implementation checklist

**Primary goal:** make the complete Guided Operations website meet or exceed the reference's refined, high-end visual quality while keeping every officer and administrator workflow clear, fast, and accessible.

**Progress note (2026-08-20):** Foundation/Home and shared shell passes were revised against the supplied reference PNG. The implementation adopts its stronger angled shell/hero composition, raised mountain scenery, continuous fence crop, compact action anatomy, content density, and Quick Access rail while excluding the screenshot's invented identity, records, notifications, health details, checklist, activity, quote, date, and version. The current working candidate based on `0038ae5` passes TypeScript, 175 component tests across 44 files, the production build, and 123 of 124 Chromium officer/admin/responsive/accessibility/print/visual-regression workflows; the one skip accurately reports that this Chromium build cannot emulate `prefers-reduced-data`, while the request-free CSS fallback has a deterministic source-contract test. All 48 Windows visual baselines pass unchanged. Local backend evidence includes 41 contract/security tests and 1,440 unit tests (30 skipped); exact predecessor `0038ae5` passed all 20 PR checks with a clean merge state. Manual screen-reader, native on-screen-keyboard, physical Windows display-scaling/high-contrast, performance p75, generated-asset production approval, and owner-release acceptance remain open. Checklist reconciliation: 289 of 332 items are complete; 43 remain open.

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
- [x] No sample or invented operational data is used as a production fallback.

---

## Phase 0 — Protect the Existing Product Before Styling

### Source-of-truth inventory

- [x] Confirm `App.tsx` remains the active authenticated application shell.
- [x] Confirm `OfficerHomePage.tsx` remains the production, data-driven Home implementation.
- [x] Treat `guided-operations.css` and `officer-home.css` as the initial active shell/Home sources while consolidation is in progress.
- [x] Inventory every stylesheet imported by the active shell and Home route.
- [x] Identify selectors from `guided-operations.css`, `refinement.css`, `sidebar-scenery.css`, and feature styles that affect the same elements.
- [x] Inventory import-order overrides in `home-refinement.css` and `styles.css` so the finished appearance does not depend on stylesheet order.
- [x] Confirm whether `HomePage.tsx`, `OfficerWorkspaceLayout.tsx`, `App.css`, and their related styles are dormant.
- [x] Record all tests that still import dormant components before removing anything.
- [x] Remove duplicate shell/Home implementations only after their useful patterns have been migrated and their imports are proven unused.
- [x] Add a route regression test proving `/` renders the authorized, data-backed Home rather than the static reference component.
- [x] Keep all existing navigation destinations and route authorization behavior unchanged.

### Baseline capture

- [x] Capture the current Home page at 1536×1024, 1366×768, 1280×800, 1024×768, 768×1024, and 390×844.
- [x] Capture the current officer navigation open and closed on tablet/mobile.
- [x] Capture representative officer pages: New Report, Reports, Document Studio, Policy Expert, Forms Library, Count Sheet, and Account.
- [x] Capture representative administrator pages: Overview, All Incidents, Paperwork Center, Accounts & Staff, Audit, Health, and Review Lab.
- [x] Record current keyboard focus order and visible focus treatments.
- [x] Record current bundle sizes and important route chunk sizes.
- [x] Run the existing component, typecheck, build, and Playwright gates before visual work begins.

### Non-regression rules

- [x] Do not replace live incident, form, count-sheet, staff, health, or session data with screenshot examples.
- [x] Do not change permissions, API payloads, route ownership, persistence, revision, or audit behavior as an incidental styling task.
- [x] Do not make print layouts inherit screen-only shadows, backgrounds, imagery, or navigation.
- [x] Do not add new dashboard panels until their data source, authorization, loading, empty, and error behavior are defined.
- [x] Do not add decorative assets containing real people, real facilities, readable signage, vehicle plates, employee identifiers, or historical records.

### Known baseline defects to correct

- [x] Increase current 40–42px Home CTA controls to at least 44px where they are primary/touch targets.
- [x] Replace white text on the current light-gold gradient; measured contrast is approximately 1.90:1 at the light stop and 3.65:1 at the dark stop.
- [x] Darken or enlarge current muted copy where `#63758A` on `#F4F8FB` measures approximately 4.43:1 and narrowly misses normal-text AA.
- [x] Strengthen the current semi-transparent focus treatment; its approximate 1.80:1 contrast does not provide a dependable 3:1 component/focus boundary.
- [x] Disable the Home card's hover translation itself in reduced-motion mode instead of only removing its transition duration.
- [x] Preserve the current scenic SVGs' very small transfer-size baseline when replacing their generic artwork with higher-fidelity assets.

---

## Phase 1 — Establish the Shared Visual System

### Color tokens

- [x] Define one canonical token file for canvas, surface, raised surface, inset surface, borders, text, muted text, navy, blue, gold, success, warning, danger, neutral, focus, and disabled colors.
- [x] Keep the visual balance near 80% light surfaces, 15% navy structure, and 5% gold/semantic accents.
- [x] Use navy for structure, navigation, headings, and high-confidence secondary actions.
- [x] Reserve gold for the selected navigation item, the single primary action in a context, and small premium accents.
- [x] Avoid using gold for large text blocks, routine metadata, or every interactive control.
- [x] Use dark navy text on light gold where white text does not meet contrast.
- [ ] Test every text/background combination instead of assuming gradients pass contrast.
- [x] Define semantic colors independently from decorative gold/blue so status meaning never depends on branding color.

Evidence: `guided-operations.css` owns the shared `--gow-*` canvas, surface, ink, muted, border, focus, disabled, danger, success, warning, and brand tokens; administrator aliases resolve back to those semantic values.

### CSS consolidation

- [x] Consolidate active shell styling into one maintained shell stylesheet.
- [x] Consolidate active Home styling into `officer-home.css` or an equally explicit feature-owned module.
- [x] Move active sidebar scenery rules into the maintained shell layer.
- [x] Split genuinely administrator-specific refinements away from global officer styles.
- [x] Remove duplicate hero, action-card, button, sidebar, and status selectors after visual parity is confirmed.
- [ ] Replace separate `--gow-*`, `--admin-*`, Count Sheet, and dormant prototype color values with shared semantic tokens plus necessary feature aliases.
- [x] Remove the stale `assets/sidebar-mountains.jpg` reference after confirming it is not part of the supported build.
- [x] Keep official paperwork print rules isolated from all decorative screen tokens.
- [x] Do not make production typography depend on a public font CDN being reachable from the facility network.

### Typography

- [x] Use one highly legible sans-serif stack for navigation, controls, forms, tables, and body copy.
- [x] Define tokens for display heading, page heading, panel heading, body, supporting copy, label, metadata, and compact table text.
- [x] Keep body text at least 16 CSS pixels on mobile and avoid dense desktop text below 12 CSS pixels.
- [x] Use a display serif only for a small brand or quotation treatment if it remains legible and does not spread into operational UI.
- [x] Tighten large Home greeting typography without clipping long names or browser zoom.
- [x] Prevent all-caps tracking from reducing readability in small labels.
- [x] Use tabular numerals where aligned counts, dates, times, or incident numbers benefit from them.

Evidence: canonical type tokens and system stacks live in `guided-operations.css`; Home long-name, 200%, and 400% tests pass, and the administrator shell applies a screen-only 12px compact-text floor without changing print or dense-grid geometry.

### Spacing, radii, borders, and elevation

- [ ] Define a spacing scale and remove one-off gaps that create uneven density.
- [ ] Define small, medium, and large surface radii; avoid a different radius on every component.
- [x] Define separate border tokens for standard, strong, focus, warning, and destructive states.
- [x] Define three elevation levels: control, card, and feature fixture.
- [x] Keep data tables and dense editors mostly flat for scanning performance.
- [x] Use deeper elevation only for primary action fixtures, active navigation, print stacks, and important dialogs.
- [x] Ensure shadows remain visible but subtle on common Windows displays.
- [x] Remove double shadows and nested raised surfaces that make the interface look inflated.

### Icon system

- [x] Select one coherent SVG icon family for navigation and routine actions.
- [x] Standardize stroke/fill weight, optical size, alignment, corner style, and active-state treatment.
- [x] Replace text glyphs such as `›`, `→`, `◇`, `▤`, and `⌄` in functional controls with accessible SVG icons.
- [x] Keep decorative fixture artwork separate from the routine interface icon family.
- [x] Ensure icon-only controls have accessible names and visible tooltips where meaning is not obvious.
- [x] Mark purely decorative icons and artwork as hidden from assistive technology.

Evidence: the typed `InterfaceIcon` component standardizes a 24px view box, current-color 1.8px strokes, rounded joins/caps, decorative `aria-hidden`, and optional titled informational icons; its accessibility behavior has focused component tests.

### Motion

- [x] Define 120–180ms control feedback and 180–240ms navigation/panel transitions.
- [x] Limit movement to small position changes, shadow compression, opacity, and active-state transitions.
- [x] Give raised buttons approximately 2px of pressed travel with a compressed contact shadow.
- [x] Avoid delayed entrances, continuous motion, parallax, looping glows, or decorative animation during operational work.
- [x] Make reduced-motion mode remove travel while preserving immediate state/color feedback.

---

## Phase 2 — Create the Visual Assets

### Top prison/watchtower hero scene

- [x] Produce a fictional, non-identifying correctional perimeter scene with sunrise light, fence silhouette, and watchtower.
- [x] Keep the image calm and professional; avoid inmates, weapons, emergency activity, threatening weather, or dramatic surveillance imagery.
- [x] Compose the brightest and lowest-detail area behind the greeting text.
- [x] Place the watchtower and fence detail toward the right so they do not compete with the employee name.
- [x] Include sufficient bleed for wide desktop crops without cutting off the tower.
- [x] Create alternate crops for wide desktop, standard desktop, tablet, and mobile.
- [x] Provide AVIF/WebP delivery plus a dependable fallback.
- [ ] Define explicit width, height, and aspect ratio to prevent layout shift.
- [x] Add a CSS light-edge fade or scrim rather than permanently washing out the source artwork.
- [x] Verify legibility with short and very long fictional employee names.
- [x] Verify the asset at normal, high-contrast, forced-colors, and reduced-data conditions.
- [x] Provide a gradient-only fallback when the image cannot load.
- [x] Keep hero artwork out of printed pages.

Evidence: asset tests now verify the intrinsic canvas dimensions of every responsive WebP and the CSS aliases that select each crop, while the existing min-height/CLS workflow proves stable observed layout. The stronger requirement for explicit rendered width, height, and aspect ratio remains open because the attempted aspect-ratio rule changed approved tablet/mobile crops.

### Left mountain scene

- [x] Produce or refine a fictional mountain landscape for the lower sidebar.
- [x] Keep the upper navigation area solid enough to preserve label and icon contrast.
- [x] Fade the mountain scene into navy before it reaches navigation links.
- [x] Keep scenic detail strongest near the bottom and progressively quieter upward.
- [x] Ensure the scene works at the permanent desktop sidebar width and the wider mobile drawer width.
- [x] Prevent the scenery from intercepting pointer or keyboard interaction.
- [x] Use optimized dimensions and formats rather than loading a full-screen photograph into a narrow rail.
- [x] Provide a solid navy fallback with no layout change.
- [x] Confirm the artwork never appears behind print output.

### Brand crest and feature fixtures

- [x] Decide whether the current code-native shield remains or an approved fictional crest replaces it.
- [x] If a crest is added, keep the product name code-native and the crest decorative.
- [x] Produce four visually related fixtures for Incident Report, Count Sheet, Policy Question, and Forms Library.
- [x] Use consistent perspective, light direction, material finish, border treatment, and shadow softness across fixtures.
- [x] Keep fixture dimensions stable so action-card text does not jump while assets load.
- [x] Avoid photorealistic staff portraits or facility-specific insignia.
- [ ] Verify every generated asset is licensed/approved for repository and production use.
- [x] Record the source, license, generation method, approval, and privacy review for every scenic or fixture asset.
- [x] Sanitize SVG assets and reject scripts, remote references, tracking, embedded raster metadata, or unsafe markup.
- [x] Choose one maintained source for each scene and document how Vite publishes it; do not hand-edit generated backend build output.

---

## Phase 3 — Refine the Application Shell

### Desktop sidebar

- [x] Preserve exactly Home, New Report, Reports, Policy Expert, Forms Library, and Account for officers.
- [x] Keep the Administration entry role-gated and visually separated without creating a second competing navigation system.
- [x] Rebuild the brand block with a controlled curved or angled lower-right edge inspired by the reference.
- [x] Keep the gold separator crisp and restrained.
- [x] Integrate the mountain scene into the lower rail without placing text over high-detail terrain.
- [x] Standardize nav-row height, horizontal padding, icon box, label baseline, and vertical gap.
- [x] Make the active nav item unmistakable through shape, color, and position—not color alone.
- [x] Expose the active destination with `aria-current="page"`.
- [x] Give hover, focus, pressed, and active states distinct treatments.
- [x] Keep every nav target at least 44×44 CSS pixels.
- [x] Remove detailed service health from the sidebar.
- [x] Keep only a compact brand tagline or safe session note at the bottom.
- [x] Show a version only when sourced from real build metadata.
- [x] Verify sidebar scrolling does not hide primary navigation at 768px-tall displays.

### Top utility bar

- [x] Visually integrate the top utility controls with the hero edge on Home.
- [x] Use a simpler neutral topbar on working pages so it does not reduce editor/document space.
- [x] Separate network connectivity, last successful refresh, and backend service health.
- [x] Show `Online`, `Reconnecting`, or `Offline` only from actual connectivity state.
- [x] Show last refreshed/synced time only from a trustworthy timestamp.
- [x] Add notifications only when backed by an actionable, authorized source.
- [ ] Provide an honest zero-notification state.
- [x] Convert the profile chip into a real button with `aria-expanded` and keyboard-operated menu behavior.
- [x] Include Account, role/shift context, session status, and Sign Out in the menu.
- [x] Use initials as the default privacy-safe identity treatment.
- [x] Add an avatar only after defining an approved source, storage, fallback, and revocation behavior.

### Main workspace frame

- [x] Add a centered maximum-width content container for Home so ultrawide screens do not create a large empty field.
- [x] Use disciplined left/right gutters aligned with the hero and card grid.
- [x] Keep report, form, table, and editor routes able to use wider working space than Home.
- [x] Avoid applying a permanent Home utility rail to Document Studio, Count Sheet, Paperwork Center, or other dense workspaces.
- [x] Preserve a predictable page-header location on every non-Home route.

---

## Phase 4 — Refine the Officer Home Page

### Hero

- [x] Use the prison/watchtower scene only on Home, not as a banner repeated on every route.
- [x] Render the signed-in employee’s real authorized display name dynamically.
- [x] Keep greeting time-of-day logic accurate or use a neutral greeting when client time is unreliable.
- [x] Decide whether shift belongs in the hero or profile menu; avoid repeating it in both at equal emphasis.
- [ ] Keep the supporting message short, calm, and approved.
- [x] Preserve Professionalism, Accountability, and Integrity as secondary detail rather than primary navigation.
- [x] Ensure the hero remains useful when the image fails or the user increases text size to 200%.

### Primary action cards

- [x] Keep exactly four primary action cards: New Incident Report, Count Sheet, Policy Question, and Forms Library.
- [x] Remove decorative `01`–`04` watermark numbers.
- [x] Use one fixture, one heading, one short supporting sentence, and one clear action per card.
- [x] Keep action labels concise: Start, Open, Ask, and Browse.
- [x] Preserve existing routes and accessible link names.
- [x] Keep only the highest-priority action gold; use refined navy/blue for the other actions.
- [x] Align fixture size, heading position, body-copy height, and button baseline across all four cards.
- [x] Prevent fixed text heights from clipping translated, zoomed, or longer copy.
- [x] Make the whole card feel cohesive without turning the whole surface into an ambiguous click target.
- [x] Add loading and disabled states only where the action genuinely has asynchronous availability.
- [x] Surface today’s Count Sheet state compactly in its card when available.

### Card finish

- [x] Use a quiet white-to-cool-white surface gradient.
- [x] Add one fine border, one subtle top highlight, and one restrained contact shadow.
- [x] Avoid glass blur on every card; reserve transparency for the shell/topbar if needed.
- [x] Keep card content contrast independent of background artwork.
- [x] Use consistent internal padding and vertical rhythm.
- [x] Use hover elevation only on interactive cards and disable travel for reduced motion.
- [x] Keep static information panels visually quieter than action cards.

### Continue, incidents, and forms

- [x] Restyle Continue Your Work as the strongest data panel below the actions.
- [x] Keep incident number first, incident name second, progress state, updated time, and one Continue action.
- [x] Remove decorative metrics that do not help the officer decide what to do next.
- [x] Make Recent Incidents rows fully clickable with clear focus and hover states.
- [x] Preserve computed workflow progress; do not copy sample status labels from the reference.
- [x] Keep relative times paired with machine-readable timestamps where applicable.
- [x] Call forms `Frequently Used` only if ranking is real; otherwise use `Quick Forms` or `Common Forms`.
- [x] Show print actions only for forms whose capability permits printing.
- [x] Preserve physical-only guidance instead of presenting a fake digital form.

### Desktop utility rail

- [x] Implement the right utility rail on wide Home layouts where it does not compress the primary cards.
- [x] Limit the initial rail to Quick Access, summarized System Status, and Help.
- [x] Build Quick Access from existing valid destinations.
- [x] Give Daily Paperwork a real authorized destination before exposing it as a shortcut.
- [ ] Keep service health summarized as Operational, Degraded, Unavailable, or Unknown.
- [x] Do not reveal database hosts, model configuration, credentials, raw exceptions, or infrastructure topology.
- [x] Point Help to a real approved destination; omit the panel until one exists.
- [x] Move the rail below primary content at medium desktop widths.
- [x] Do not hide rail functions on mobile; relocate essential shortcuts into the content flow.

Evidence: Home component and route tests assert the four actions, authorized data fetch, computed incident content, Quick Forms naming, responsive Quick Access destinations, profile/session behavior, and fictional-data boundaries.

### Lower-priority panels

- [x] Add a daily checklist only after its date, shift, role, ownership, and completion semantics are defined.
- [x] Treat checklist circles as status indicators unless the officer is explicitly permitted to change completion.
- [x] Add recent activity only from safe, personal, authorization-scoped event summaries.
- [x] Exclude narratives, form values, policy prompts, credentials, raw audit payloads, and other employees’ activity.
- [x] Avoid repeating the same destination in primary actions, Quick Access, Quick Links, and Help unless usage testing proves the redundancy useful.
- [x] Keep any quote/trust strip visually subordinate and remove it on narrower layouts if it adds noise.
- [x] Use locale-aware date/time only if it helps the task; do not create a constantly updating decorative clock.

---

## Phase 5 — Refine Cards and Buttons Site-Wide

### Button system

- [x] Create canonical primary, secondary, destructive, quiet/text, icon-only, and segmented-control variants.
- [x] Use a refined gold primary treatment only for the dominant action.
- [x] Use a navy/blue raised treatment for normal affirmative actions.
- [x] Keep destructive actions red and visually separate from brand gold.
- [x] Include top highlight, darker lower edge, restrained shadow, and approximately 2px active travel.
- [x] Define hover, focus-visible, active, loading, disabled, and selected states for every variant.
- [ ] Keep button text and icons centered at all supported zoom levels.
- [x] Keep minimum height at 44px for primary/mobile controls and adequate width for comfortable targeting.
- [x] Prefer 48px height for the four major officer actions and keep at least 8px between adjacent touch targets.
- [x] Never rely on shadow alone to communicate disabled or selected state.
- [x] Apply hover-only elevation inside `@media (hover: hover)` so touch devices do not retain misleading hover states.

Evidence: the typed `Button` primitive publishes primary, secondary, destructive, quiet, icon-only, and segmented variants from one class contract. Shared CSS supplies hover, global focus-visible, active travel, disabled, and selected treatments; the primitive exposes loading through disabled plus `aria-busy` and selected through `aria-pressed` plus `data-selected`. Focused component tests cover every variant and the loading/selected accessibility contract.

### Shared cards and panels

- [x] Create reusable surface variants for action card, information panel, list panel, inset row, empty state, warning, and dialog.
- [ ] Standardize header spacing, heading hierarchy, optional action placement, and body padding.
- [ ] Use one list-row pattern for chevron navigation and another explicit pattern for actions such as Print or Open.
- [x] Keep status chips semantically consistent across Home, Reports, Document Studio, Administration, and Paperwork Center.
- [ ] Avoid nested card-within-card-within-card layouts.
- [x] Keep admin density higher through spacing and information layout, not by abandoning the visual system.

### Form and data controls

- [ ] Standardize input, select, textarea, search, checkbox, radio, switch, date, and time controls.
- [x] Define normal, hover, focus, populated, disabled, read-only, invalid, and successful states.
- [x] Keep labels visible; do not use placeholder text as the only label.
- [ ] Keep required/optional and validation language consistent.
- [x] Preserve dense table scanning and keyboard entry in operational paperwork editors.
- [x] Keep sticky headers and horizontal scrolling deliberate on narrow data views.

Evidence: the typed `Surface` primitive publishes action, information, list, inset, empty, warning, and dialog variants backed by shared semantic tokens. The shared `Field`/`.gow-control` contract defines base, hover, focus-visible, populated, disabled, read-only, invalid, and successful states and programmatically connects visible labels, hints, required text, and invalid messaging. Representative Policy Expert and Account fields consume the primitive; full site-wide control migration and copy consistency remain open.

---

## Phase 6 — Apply the System Page by Page

### Officer routes

- [x] Home: complete the hero, primary actions, core panels, and optional utility rail.
- [x] New Report: clarify the single next step and keep AI/data provenance visible.
- [x] Reports: refine search, filters, incident rows, status chips, loading, and empty states.
- [x] Document Studio: preserve maximum writing/review space and keep decorative depth minimal.
- [x] Policy Expert: refine question entry, citations, source cards, and answer confidence without making AI look infallible.
- [x] Forms Library: refine category/search controls, capability labels, physical-only guidance, and print actions.
- [x] Count Sheet: preserve keypad/table efficiency while applying shared controls and surface tokens.
- [x] Account: refine identity, session, PIN, sign-out, and security states without unnecessary decoration.

### Administrator routes

- [x] Overview: use the shared system with denser information hierarchy and clear exceptions.
- [x] All Incidents: standardize filters, attributed rows, status chips, and admin actions.
- [x] Paperwork Center: preserve working width and print behavior while standardizing tabs, cards, forms, and save states.
- [x] Accounts & Staff: standardize sensitive actions, step-up prompts, temporary PIN presentation, and session controls.
- [x] Audit: prioritize scanability and redaction over dimensional decoration.
- [x] Health: use semantic status hierarchy without exposing unsafe infrastructure details.
- [x] Review Lab: preserve its approved operational workflow and handoff safeguards.

### Shared states

- [x] Provide refined skeletons that match final geometry.
- [x] Provide honest empty states with a useful next action when one exists.
- [x] Provide reconnecting/offline states that distinguish local input preservation from server persistence.
- [x] Standardize unsaved, saving, saved, conflict, failed, and retry states.
- [ ] Standardize warning, destructive confirmation, success, and dependency-unavailable messaging.
- [x] Keep error recovery controls keyboard reachable and descriptive.

Evidence: one shared persistence-status catalog and error classifier now give New Report, Count Sheet, Document Studio copy and officer-report editors, and all six active Daily Paperwork editors the same truthful unsaved, saving, saved, reconnecting, conflict, and failed language. Network-unavailable and revision-conflict errors never claim a save and keep visible input intact; network or terminal failures expose retry controls, while revision conflicts block stale resubmission and direct the employee to copy the visible text before reopening the latest report. Deterministic classifier/component tests cover network, conflict, terminal failure, visible-input preservation, and retry presentation; the browser outage/retry workflow proves `server save not confirmed` followed by `Saved to server` after a successful retry.

---

## Phase 7 — Responsive and Windows Usability

### Wide and standard desktop

- [ ] Match the intended visual quality at approximately 1536×1024 without copying demonstration data.
- [x] Verify 1366×768 without clipped buttons, hidden panel actions, inaccessible sidebar items, or excessive empty canvas.
- [x] Verify 1280×720 and other short-height laptop layouts without shrinking controls below usable sizes.
- [x] Keep the utility rail only when the remaining main column is comfortably readable.
- [x] Switch four action cards to a 2×2 layout before labels become compressed.
- [x] Verify Windows display scaling at 100%, 125%, and 150%.
- [ ] Verify browser zoom at 80%, 100%, 125%, 150%, 200%, and 400% where WCAG reflow applies.

### Tablet

- [x] Convert the permanent sidebar to an accessible drawer or compact rail.
- [x] Preserve the hero greeting and immediately useful actions without oversized artwork.
- [x] Use purpose-built two-column/one-column panel ordering.
- [x] Keep drawers dismissible by close button, scrim, and Escape.
- [x] Restore focus to the menu trigger after closing.

### Mobile

- [x] Verify approximately 390×844 and 360×800 layouts.
- [x] Verify 430×932, 320×568, and approximately 844×390 mobile landscape layouts.
- [x] Use a one-column action stack with concise descriptions.
- [x] Keep Count Sheet, New Report, Reports, Policy Expert, Forms, and Account immediately reachable.
- [x] Prevent horizontal page overflow.
- [x] Allow tables to use a labeled, contained horizontal-scroll region where unavoidable.
- [x] Avoid hiding operational status, error recovery, checklist, or support solely to simplify the screen.
- [ ] Keep fixed/sticky elements from covering form controls when the on-screen keyboard opens.
- [x] Respect safe-area insets for mobile navigation and bottom controls.
- [x] Prevent background scrolling while the navigation drawer is open.

---

## Phase 8 — Accessibility Acceptance

- [ ] Meet WCAG 2.2 AA contrast for text, icons, borders needed for understanding, focus indicators, and control states.
- [x] Test gold buttons in every gradient position; use navy text or a darker gold when white fails.
- [ ] Meet 44×44 CSS pixel target guidance for primary and touch interactions.
- [ ] Provide visible `:focus-visible` states that are not clipped by overflow or shadows.
- [ ] Verify logical keyboard order through sidebar, utility bar, hero actions, panels, menus, drawers, and dialogs.
- [x] Verify Enter/Space activation and Escape dismissal where expected.
- [x] Give menus, notifications, disclosure controls, and dialogs correct names, states, and relationships.
- [ ] Announce save, reconnect, validation, loading completion, and recoverable error states appropriately.
- [x] Keep artwork decorative unless it conveys information unavailable in text.
- [x] Verify text resizing to 200% without clipping or loss of controls.
- [x] Verify 400% zoom/reflow for appropriate non-document pages.
- [x] Test with forced colors/high contrast and ensure selected/active/status states remain understandable.
- [x] Test reduced motion and confirm no required information depends on animation.
- [x] Test screen-reader navigation landmarks and heading order on every primary route.

Evidence: officer and administrator gold actions now use dark navy text; token tests enforce 4.5:1 contrast for the active gold, muted-copy, and ten rendered semantic-status pairs, plus a 3:1 focus boundary on common light surfaces. The shared focus token is opaque, forced-colors assertions cover current-page and keyboard-focus semantics, and achromatopsia emulation verifies that administrator status meaning remains explicit in text. Accessibility smoke tests now scan every representative officer and administrator route for unnamed interactive controls, missing image alternatives, duplicate IDs, broken labeling/description/error references, positive tabindex, and nested interactive elements. They also measure rendered focus indicators against viewport and overflow-clipping bounds while exercising profile-menu arrow order, mobile-drawer close-to-navigation order and focus restoration, and administrator dialog PIN-to-Cancel order. `officer-route-reflow.spec.ts` covers Forms Library, Policy Expert, and Account controls at 200% and 400% root text size; focused tablet/mobile checks now include all Document Studio tabs, the Forms selection label, and Random Searches section navigation with measured 44px targets, centered labels, visible unclipped focus, and logical Tab order. This durable automated evidence does not claim a complete site-wide target/focus/order audit, native on-screen-keyboard, full WCAG, physical high-contrast, or manual screen-reader acceptance; those remain open.

---

## Phase 9 — Performance and Production Integrity

- [x] Set route-specific budgets for Home JavaScript, CSS, and visual assets.
- [x] Keep combined initial scenic imagery near or below 350KB on desktop and 180KB on mobile unless measured evidence supports a larger budget.
- [x] Keep large decorative assets out of non-Home route chunks.
- [x] Preload only the Home hero image that materially improves first render.
- [x] Lazy-load below-the-fold illustrations and noncritical fixtures.
- [x] Use responsive image sources and avoid serving the 1536px reference crop to a narrow phone.
- [x] Treat a raster/photo hero as the Home LCP asset: load it early and do not lazy-load it.
- [x] Ensure image failure never removes navigation, labels, or actions.
- [x] Verify no layout shift when hero, sidebar, crest, or fixtures load.
- [x] Confirm Vite-hashed assets receive immutable caching and the SPA document remains `no-store`.
- [x] Confirm Content Security Policy permits the selected same-origin asset strategy without unsafe inline scripts.
- [x] Confirm production images contain no source reference screenshot, uploaded design drafts, real identities, or unintended metadata.
- [x] Verify scenic assets load from the production static path in the Cloud Run image.
- [ ] Meet production p75 goals of LCP ≤2.5s, CLS ≤0.1, and INP ≤200ms.

Evidence: `visual-assets.test.ts` enforces image size and metadata/privacy guards; Home preloads a single media-matching responsive WebP candidate, the sidebar is dimensioned/lazy/low-priority, and Playwright proves image-failure operability and observed CLS no greater than 0.1.

---

## Phase 10 — Visual Regression and Release Gate

### Automated coverage

- [ ] Add stable fictional Home fixtures for populated, loading, empty, error, reconnecting, and reduced-motion states.
- [x] Add desktop screenshots at 1536×1024 and 1366×768.
- [x] Add Windows-scaled or equivalent browser-zoom screenshots for 125% and 150% review.
- [x] Add tablet screenshots in portrait and landscape.
- [x] Add mobile screenshots at 390×844 and 360×800.
- [x] Add 430×932, 320×568, and mobile-landscape references for edge-case review.
- [ ] Add sidebar/drawer open, profile menu open, notification state, keyboard focus, and error-state references.
- [x] Add forced-colors references or assertions for navigation, cards, buttons, status, and focus.
- [x] Add representative screenshots for every officer and administrator route after shared-token migration.
- [x] Mask or use fictional data in every screenshot, video, trace, and report.
- [x] Keep print screenshots separate and verify screen decoration does not enter print output.

Evidence: 48 Chromium/Windows baselines cover Home viewports and states, drawer/profile/focus, 125%/150% device scaling, desktop and mobile versions of every primary officer route, every administrator route, administrator mobile navigation, and six isolated print layouts. The 1536px and tablet-portrait Home references reflect removal of redundant Home content. Fictional API fixtures and stable masks prevent operational data from entering artifacts; all baselines pass on the candidate and the new mobile and print outputs were inspected directly.

### Manual visual review

- [x] Compare hero crop, text-safe area, watchtower placement, sidebar fade, card density, button depth, icons, spacing, and alignment against the approved visual cues.
- [ ] Confirm the result feels polished without copying every panel or piece of demonstration content from the reference.
- [x] Confirm the visual hierarchy remains obvious during real loading, empty, error, and incomplete-data states.
- [x] Check common Windows laptop displays for muddy shadows, low-contrast borders, and overly small metadata.
- [x] Check grayscale readability for status and print-related screens.
- [x] Record every intentional deviation with a usability, accessibility, security, performance, or data-integrity reason.

### Required verification

- [x] Run frontend component tests.
- [x] Run TypeScript checking.
- [x] Run the production frontend build and review bundle output.
- [x] Run officer Playwright workflows.
- [x] Run administrator Playwright workflows.
- [x] Run desktop, tablet, mobile, keyboard, and reduced-motion paths.
- [ ] Run automated accessibility checks and complete a manual keyboard/screen-reader pass.
- [x] Review failed-test screenshots, videos, and traces before accepting updates.
- [x] Verify the complete print suite after every shared CSS change.
- [x] Require all CI and release gates to pass before merging each visual milestone; predecessor `2249940` passed every PR check, and follow-on source candidate `f6f23c1` remains subject to the exact final PR gate.

Evidence: the current working candidate based on `0038ae5` passes 175 component tests across 44 files, TypeScript, the Vite production build (26.68 kB CSS gzip and 136.41 kB JavaScript gzip), and 123 of 124 Chromium workflows, including all 48 Windows visual baselines without snapshot updates. The expanded visual set was reviewed directly; it deliberately includes mobile/print references and loaded fictional Reports records. The single skipped workflow is the feature-detected `prefers-reduced-data` browser assertion that current Chromium cannot emulate through CDP; `visual-assets.test.ts` separately proves the request-free reduced-data CSS contract. Local backend evidence includes 41 contract/security tests and 1,440 unit tests with 30 intentional skips. Exact predecessor `0038ae5` passed all 20 PR checks with a clean merge state; the follow-on candidate still requires its own PR gate. Manual screen-reader, native on-screen-keyboard, physical high-contrast, production p75, and owner-release approval remain separate open gates.

---

## Recommended Delivery Milestones

### Milestone V1 — Foundation and shell

- [x] Reconcile active/dormant frontend implementations.
- [x] Establish tokens, icon family, button system, card system, focus, and motion.
- [x] Implement the mountain sidebar and shell refinements.
- [x] Verify all existing routes before moving forward.

### Milestone V2 — Home visual transformation

- [x] Implement the prison/watchtower hero.
- [x] Implement four refined primary action cards and fixtures.
- [x] Restyle Continue Your Work, Recent Incidents, Quick Forms, and Count Sheet status using existing data.
- [x] Complete Home responsive and accessibility checks.

### Milestone V3 — Data-backed utilities

- [x] Add Quick Access from existing routes.
- [ ] Add safe summarized System Status only after its contract is approved.
- [ ] Add Help only with a real destination.
- [ ] Add notifications, daily checklist, and activity only after each data contract and authorization rule is approved.

### Milestone V4 — Site-wide propagation

- [x] Apply shared tokens and components across all officer routes.
- [x] Apply the same system at administrator density across all admin routes.
- [x] Preserve Document Studio, paperwork editing, and print working space.

### Milestone V5 — Formal acceptance

- [ ] Complete all responsive, accessibility, performance, visual-regression, and print gates.
- [ ] Complete owner review using the actual application with fictional data.
- [ ] Resolve every material, fixable mismatch.
- [ ] Mark Site-Wide Visual Polish complete only after the production build—not a static mockup—meets the agreed quality bar.
