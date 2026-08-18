# Prison Policy Web Companion

React + TypeScript browser companion for the unified Access + web platform described in:

- `docs/superpowers/specs/2026-08-18-web-companion-unified-platform-design.md`
- `docs/superpowers/plans/2026-08-18-browser-auth-session-adapter.md`
- `docs/superpowers/plans/2026-08-18-officer-web-companion.md`
- `docs/superpowers/plans/2026-08-18-admin-web-companion.md`

## What this foundation includes

- responsive authenticated application shell;
- employee-number + PIN sign-in and required PIN-change states;
- Officer dashboard and quick actions;
- Policy Expert conversation with citation inspector;
- owned/prepared report library;
- field notes → details → draft → review report workspace;
- policy library and document-viewer design;
- session-memory saved reports and citations;
- account, PIN, and device-session controls;
- role-gated Administrator overview, staff/accounts, all-reports, audit, and health designs;
- a design-preview mode using fictional data only.

This is the **frontend foundation**, not the completed cutover. The secure Flask `/web-auth/*` and `/web-api/*` browser adapters in the implementation plans remain prerequisites for production use. Live mode never falls back to preview authentication or silently treats a failed save as successful.

## Security boundaries

- React never receives or stores renewal credentials.
- Requests use same-origin cookies and send the readable CSRF cookie on unsafe methods.
- No application data, tokens, report text, citations, or account state is written to `localStorage`, `sessionStorage`, IndexedDB, or a service-worker cache.
- Saved reports/citations and Policy Expert conversation state live in React memory only and are cleared at sign-out.
- Fictional preview data is enabled only when `VITE_DESIGN_PREVIEW=true`.
- Server authorization remains authoritative; hidden navigation is not an authorization control.

## Run the design preview

```bash
cd web-client
npm install
npm run dev:preview
```

Useful preview routes:

- Officer dashboard: `/`
- Administrator overview: `/?role=admin` or `/admin?role=admin`
- Signed-out screen: `/sign-in?signedout=1`
- Policy Expert: `/policy`
- New report: `/reports/new`

The Vite proxy expects the Flask app at `http://localhost:8080` for `/web-auth`, `/web-api`, and `/static` during live integration.

## Validation and production build

The dependency-free foundation guard can run before package installation:

```bash
cd web-client
npm run validate:foundation
```

Run the complete frontend verification after installing dependencies:

```bash
cd web-client
npm install
npm run validate:foundation
npm test
npm run build
```

The build outputs to `web-client/dist/`. Flask static serving and SPA fallback wiring are part of the web cutover workstream and should be added only after browser-auth and browser-API tests pass.

## Next implementation sequence

1. Implement and test secure browser cookies, login/session, renewal, CSRF, and no-store behavior.
2. Add the `/web-api` actor boundary and adapt Officer report, job, policy, account/session routes.
3. Connect and test the Officer pages against fictional server data.
4. Add purpose-specific Administrator step-up and connect Admin routes.
5. Add component, browser, cross-client, and cutover acceptance tests.
