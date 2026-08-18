# Officer Web Companion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the React + TypeScript Officer experience for sign-in, dashboard, reports, history, policy chat, exports, and account/session controls using the centralized platform.

**Architecture:** Create `web-client/` as a same-origin SPA built into Flask-served static assets. The client uses only `/web-auth/*` and `/web-api/*`; it never stores backend credentials or authoritative report data offline. Report and policy workflows reuse existing backend service/API contracts so Access and web operate on the same records and revisions.

**Tech Stack:** React, TypeScript, Vite, Vitest, React Testing Library, Playwright, Flask static serving.

**Spec:** `docs/superpowers/specs/2026-08-18-web-companion-unified-platform-design.md`

## Global Constraints

- Web is independently web-native; do not reproduce Access screens visually.
- Officer sees only their own reports.
- No `localStorage`, IndexedDB, or service-worker persistence for sensitive app data.
- Responsive behavior must be functional on desktop, tablet, and phone.
- Use the same report IDs/revisions as Access.

---

### Task 1: Scaffold the React client and authenticated shell

**Files:**
- Create: `web-client/package.json`
- Create: `web-client/vite.config.ts`
- Create: `web-client/src/main.tsx`
- Create: `web-client/src/app/App.tsx`
- Create: `web-client/src/api/client.ts`
- Create: `web-client/src/auth/AuthProvider.tsx`
- Create: `web-client/src/pages/SignInPage.tsx`
- Create/Test: `web-client/src/auth/AuthProvider.test.tsx`
- Modify: `backend/webapp/app.py`

**Interfaces:**
- Consumes: `/web-auth/login`, `/web-auth/session`, `/web-auth/logout`.
- Produces: `AuthProvider`, `useAuth()`, same-origin API client with CSRF header support.

- [ ] **Step 1: Write the failing auth-provider test**

```tsx
it("does not persist auth credentials in browser storage", async () => {
  render(<AuthProvider><TestProbe /></AuthProvider>);
  await screen.findByText(/signed out/i);
  expect(localStorage.length).toBe(0);
  expect(sessionStorage.length).toBe(0);
});
```

- [ ] **Step 2: Run it**

Run: `cd web-client && npm test -- AuthProvider.test.tsx`
Expected: FAIL before scaffold exists.

- [ ] **Step 3: Implement the shell**

`api/client.ts` must use `credentials: "same-origin"`, read the non-HttpOnly CSRF cookie only to populate `X-CSRF-Token` on unsafe requests, and expose typed `get/post/patch/delete` helpers. `AuthProvider` loads `/web-auth/session` at startup and stores only safe profile/session state in React memory.

- [ ] **Step 4: Run unit tests and production build**

Run: `cd web-client && npm test && npm run build`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web-client backend/webapp/app.py
git commit -m "feat(web): scaffold authenticated React client"
```

### Task 2: Implement required PIN change and account/session controls

**Files:**
- Create: `web-client/src/pages/ChangePinPage.tsx`
- Create: `web-client/src/pages/AccountPage.tsx`
- Create: `web-client/src/features/sessions/SessionList.tsx`
- Create/Test: `web-client/src/features/sessions/SessionList.test.tsx`
- Extend: `backend/webapp/web_api/` account/session routes as needed by existing identity services.

**Interfaces:**
- Consumes: browser PIN-change route, current profile, list/revoke sessions, logout-all.
- Produces: first-login redirect and account session-management UI.

- [ ] **Step 1: Write a failing required-PIN-change route test**

```tsx
it("forces pin change before showing the workspace", async () => {
  server.use(sessionRequiresPinChange());
  render(<App />);
  expect(await screen.findByRole("heading", {name: /change pin/i})).toBeVisible();
  expect(screen.queryByText(/my reports/i)).toBeNull();
});
```

- [ ] **Step 2: Run focused tests**

Run: `cd web-client && npm test -- ChangePinPage SessionList`
Expected: FAIL.

- [ ] **Step 3: Implement PIN/session flows**

After successful PIN change, refresh safe session/profile state. Session list displays device label, created/last-used time, persistence, and current-session marker. Revocation and logout-all require explicit confirmation and only report success after server confirmation.

- [ ] **Step 4: Re-run tests**

Run: `cd web-client && npm test -- ChangePinPage SessionList`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web-client/src/pages/ChangePinPage.tsx web-client/src/pages/AccountPage.tsx web-client/src/features/sessions backend/webapp/web_api
git commit -m "feat(web): add pin and session controls"
```

### Task 3: Build Officer dashboard and My Reports

**Files:**
- Create: `web-client/src/pages/HomePage.tsx`
- Create: `web-client/src/pages/MyReportsPage.tsx`
- Create: `web-client/src/features/reports/reportApi.ts`
- Create: `web-client/src/features/reports/ReportTable.tsx`
- Create/Test: `web-client/src/features/reports/ReportTable.test.tsx`
- Extend: `backend/webapp/web_api/reports.py`

**Interfaces:**
- Consumes: existing Officer report list/detail service/API with server-derived ownership.
- Produces: typed `ReportSummary`, pagination/filter helpers, dashboard recent-draft/report data.

- [ ] **Step 1: Write failing ownership/display tests**

```tsx
it("renders only report summaries returned for the signed-in officer", async () => {
  server.use(myReports([{id: "r1", status: "draft", owner_name: "Officer One"}]));
  render(<MyReportsPage />);
  expect(await screen.findByText("r1")).toBeVisible();
  expect(screen.queryByText("another-officer-report")).toBeNull();
});
```

Add a backend test proving `/web-api/reports/<other-officer-id>` returns `404` or `403` under the same semantics as `/api/v1`.

- [ ] **Step 2: Run frontend/backend focused tests**

Run: `cd web-client && npm test -- ReportTable` and `python -m pytest tests/unit/test_web_api_isolation.py -q`
Expected: FAIL until adapter/routes exist.

- [ ] **Step 3: Implement dashboard/report listing**

Use server pagination; do not fetch all reports then filter in React. Home shows active drafts, recent reports, and pending/recent AI jobs based on safe summary endpoints.

- [ ] **Step 4: Run tests**

Run: `cd web-client && npm test -- ReportTable HomePage && cd .. && python -m pytest tests/unit/test_web_api_isolation.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web-client/src/pages/HomePage.tsx web-client/src/pages/MyReportsPage.tsx web-client/src/features/reports backend/webapp/web_api/reports.py tests/unit/test_web_api_isolation.py
git commit -m "feat(web): add officer dashboard and report history"
```

### Task 4: Build the report workspace and AI job flow

**Files:**
- Create: `web-client/src/pages/ReportWorkspacePage.tsx`
- Create: `web-client/src/features/reports/ReportEditor.tsx`
- Create: `web-client/src/features/reports/RevisionBanner.tsx`
- Create: `web-client/src/features/jobs/jobApi.ts`
- Create: `web-client/src/features/jobs/JobStatus.tsx`
- Create/Test: `web-client/src/features/reports/ReportWorkspacePage.test.tsx`
- Extend: `backend/webapp/web_api/reports.py`, `backend/webapp/web_api/jobs.py`

**Interfaces:**
- Consumes: centralized draft/report revisions and AI job APIs.
- Produces: create/save/resume/generate/review/submit workflow with revision conflict handling.

- [ ] **Step 1: Write failing save/conflict/job tests**

```tsx
it("shows a revision conflict instead of claiming save succeeded", async () => {
  server.use(saveReportConflict());
  render(<ReportWorkspacePage />);
  await userEvent.click(await screen.findByRole("button", {name: /save/i}));
  expect(await screen.findByText(/newer version/i)).toBeVisible();
  expect(screen.queryByText(/saved successfully/i)).toBeNull();
});
```

- [ ] **Step 2: Run tests**

Run: `cd web-client && npm test -- ReportWorkspacePage`
Expected: FAIL.

- [ ] **Step 3: Implement report state machine UI**

Persist drafts only through server requests. Include current revision/version in mutations. On `409`, fetch latest revision and present a compare/review banner. Poll AI jobs with bounded backoff and stop on terminal state or navigation/sign-out.

- [ ] **Step 4: Run frontend and backend report/job suites**

Run: `cd web-client && npm test -- ReportWorkspacePage && cd .. && python -m pytest tests/integration/test_employee_report_api.py tests/integration/test_job_submission.py tests/integration/test_job_redelivery.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web-client/src/pages/ReportWorkspacePage.tsx web-client/src/features/reports web-client/src/features/jobs backend/webapp/web_api/reports.py backend/webapp/web_api/jobs.py
git commit -m "feat(web): add centralized report workspace"
```

### Task 5: Add report detail, revisions, and export

**Files:**
- Create: `web-client/src/pages/ReportDetailPage.tsx`
- Create: `web-client/src/features/reports/RevisionHistory.tsx`
- Create: `web-client/src/features/reports/ExportButton.tsx`
- Create/Test: `web-client/src/features/reports/RevisionHistory.test.tsx`

**Interfaces:**
- Consumes: existing authorized report detail/revision/export endpoints.
- Produces: Officer-visible revision history and safe document download.

- [ ] **Step 1: Write failing revision/export test**

```tsx
it("shows server revision history and downloads only after authorization succeeds", async () => {
  render(<ReportDetailPage />);
  expect(await screen.findByText(/revision 2/i)).toBeVisible();
  expect(screen.getByRole("button", {name: /export/i})).toBeEnabled();
});
```

- [ ] **Step 2: Run focused tests**

Run: `cd web-client && npm test -- RevisionHistory`
Expected: FAIL.

- [ ] **Step 3: Implement detail/revision/export UI**

Never construct a document from cached client state; request the server-authorized export for a concrete report/revision and stream/download the response.

- [ ] **Step 4: Run tests and export integration tests**

Run: `cd web-client && npm test -- RevisionHistory && cd .. && python -m pytest tests/integration/test_export_api.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web-client/src/pages/ReportDetailPage.tsx web-client/src/features/reports
git commit -m "feat(web): add report revisions and exports"
```

### Task 6: Add Policy Expert with citations

**Files:**
- Create: `web-client/src/pages/PolicyPage.tsx`
- Create: `web-client/src/features/policy/policyApi.ts`
- Create: `web-client/src/features/policy/PolicyConversation.tsx`
- Create: `web-client/src/features/policy/CitationPanel.tsx`
- Create/Test: `web-client/src/features/policy/PolicyConversation.test.tsx`
- Extend: `backend/webapp/web_api/policy.py`

**Interfaces:**
- Consumes: authenticated policy API/citations.
- Produces: session-memory-only conversation with cited answers.

- [ ] **Step 1: Write failing citation/unavailable tests**

```tsx
it("renders citations and does not invent an answer on service failure", async () => {
  server.use(policyUnavailable());
  render(<PolicyPage />);
  await submitQuestion("What is the rule?");
  expect(await screen.findByText(/temporarily unavailable/i)).toBeVisible();
  expect(screen.queryByText(/according to policy/i)).toBeNull();
});
```

- [ ] **Step 2: Run focused tests**

Run: `cd web-client && npm test -- PolicyConversation`
Expected: FAIL.

- [ ] **Step 3: Implement policy UI**

Keep conversation in React memory only. Clear it when auth state becomes signed-out. Render citations using server-provided source identifiers/text only; never treat previous user/assistant turns as policy evidence.

- [ ] **Step 4: Run policy tests**

Run: `cd web-client && npm test -- PolicyConversation && cd .. && python -m pytest tests/contract/test_policy_examples.py tests/unit/test_policy_v1.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web-client/src/pages/PolicyPage.tsx web-client/src/features/policy backend/webapp/web_api/policy.py
git commit -m "feat(web): add cited policy expert"
```

### Task 7: Add responsive navigation and Officer E2E acceptance

**Files:**
- Create: `web-client/src/app/AppShell.tsx`
- Create: `web-client/src/styles/`
- Create: `web-client/e2e/officer.spec.ts`
- Modify: `web-client/playwright.config.ts`

**Interfaces:**
- Produces: web-native desktop/tablet/phone navigation and complete Officer acceptance path.

- [ ] **Step 1: Write the E2E acceptance test**

The Playwright test signs in with a fictional Officer, changes a temporary PIN, creates/saves/generates/submits a fictional report, verifies it in My Reports, opens revisions, exercises Policy Expert, and signs out. Run the same core navigation at desktop, tablet, and phone viewport projects.

- [ ] **Step 2: Run E2E and confirm failures**

Run: `cd web-client && npm run test:e2e -- officer.spec.ts`
Expected: FAIL until navigation/remaining wiring is complete.

- [ ] **Step 3: Implement responsive shell**

Desktop uses persistent navigation; narrow viewports use an accessible menu/drawer. Preserve route names and semantic headings but optimize layout for browser use rather than Access parity.

- [ ] **Step 4: Run complete Officer client suite**

Run: `cd web-client && npm test && npm run build && npm run test:e2e -- officer.spec.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web-client/src/app/AppShell.tsx web-client/src/styles web-client/e2e web-client/playwright.config.ts
git commit -m "feat(web): complete officer web companion"
```
