# Guided Operations Visual Accessibility Evidence

## Keyboard and focus order

The maintained order follows DOM and task priority rather than visual positioning:

1. Mobile menu trigger when the permanent sidebar is unavailable.
2. Sidebar primary navigation in route order: Home, New Report, Reports, Policy Expert, Forms Library, Account, then the role-gated Administration entry.
3. Top utility controls: connectivity status is informational, followed by the profile-menu trigger.
4. Page heading and route-local controls in reading order.
5. Home primary actions: New Incident Report, Count Sheet, Policy Question, Forms Library; then Continue Your Work, Recent Incidents, Quick Forms, and Quick Access.
6. Working-route forms, tables, editors, and action bars in their source order. A wide Count Sheet uses a named, focusable horizontal-scroll region before its contained grid controls.

The mobile drawer moves focus to its Close control when opened. Escape, Close, and scrim dismissal return focus to the menu trigger and restore page scrolling. The profile menu supports Arrow Up/Down, Home, End, and Escape; Escape returns focus to the profile trigger. Administrator step-up and confirmation dialogs keep an explicit keyboard-reachable cancel path.

## Visible focus contract

- Interactive shell, Home, officer-route, administrator, and paperwork controls use the opaque shared focus color with an offset outline.
- Forced-colors mode preserves current-page and keyboard-focus boundaries independently from gold, gradients, or shadows.
- Card and panel overflow rules do not clip the primary focus outline in the tested Home, menu, drawer, Count Sheet, and administrator paths.
- Reduced-motion mode removes travel while retaining immediate focus, color, border, pressed, and selected feedback.

## Automated evidence

- `tests/e2e/accessibility-smoke.spec.ts` covers one main landmark, one visible page heading, named navigation, routed `aria-current`, labeled controls, profile-menu keyboard behavior, recoverable Home errors, and administrator dialog paths across every primary route.
- `tests/e2e/officer-home.spec.ts` covers drawer dismissal/focus return, touch targets, forced colors, 200% and 400% reflow, reduced motion, image failure, and layout shift.
- `tests/e2e/officer-route-reflow.spec.ts` covers Forms Library, Policy Expert, and Account at 200% and 400% text sizing, plus focused-field and primary-action reachability in a reduced-height mobile viewport. The 400% gate found and now prevents content-box overflow in all three route shells.
- Count Sheet and daily-paperwork E2E suites cover keyboard grid movement, contained horizontal scrolling, save/retry behavior, and print isolation.
- Component tests cover the typed icon accessibility contract, profile/drawer focus restoration, and long authorized employee names.
- The asset contract verifies request-free `prefers-reduced-data` CSS fallbacks. The browser assertion feature-detects this media feature because current Chromium accepts the CDP request without matching the media query; unsupported runs are reported as skipped rather than falsely passing.
- Chromium achromatopsia emulation confirms that operational and unavailable administrator statuses retain explicit text labels rather than depending on color.

## Acceptance boundary

This evidence records implemented keyboard behavior and automated accessibility smoke coverage. It does not replace a manual screen-reader pass, physical Windows high-contrast review, or owner acceptance; those remain explicit release gates in the main checklist.
