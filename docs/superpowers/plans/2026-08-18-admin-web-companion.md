# Administrator Web Companion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build full Administrator web parity for accounts, roster, organization-wide reports, attributed revisions, audit, health, and step-up protected actions.

**Architecture:** Extend the same React application and browser-auth boundary. Every Admin route depends on the server-derived Admin role and existing `/api/v1` Admin services; hidden UI is convenience only, never authorization. Sensitive mutations reuse existing purpose-specific Admin PIN step-up requirements.

**Tech Stack:** React, TypeScript, Vite, Vitest, Playwright, Flask browser adapter, existing Admin `/api/v1` services.

**Spec:** `docs/superpowers/specs/2026-08-18-web-companion-unified-platform-design.md`

## Global Constraints

- Administrators can view/edit every report; edits are attributable revisions.
- Account creation starts from an approved staff identity; there is no public signup.
- Never expose stored PINs. Temporary/reset PINs are one-time values.
- Admin step-up remains required wherever the existing API requires it.
- Officer authorization behavior must remain unchanged.

---

### Task 1: Add role-gated Admin shell and overview

**Files:**
- Create: `web-client/src/admin/AdminLayout.tsx`
- Create: `web-client/src/admin/AdminOverviewPage.tsx`
- Create: `web-client/src/admin/AdminRoute.tsx`
- Create/Test: `web-client/src/admin/AdminRoute.test.tsx`

**Interfaces:**
- Consumes: authenticated profile role and Admin safe-overview endpoint.
- Produces: Admin-only navigation and overview route.

- [ ] **Step 1: Write failing role tests**

```tsx
it("does not render admin routes for an officer", async () => {
  renderAppAs("officer", "/admin");
  expect(await screen.findByText(/not authorized/i)).toBeVisible();
});
```

- [ ] **Step 2: Run tests**

Run: `cd web-client && npm test -- AdminRoute`
Expected: FAIL.

- [ ] **Step 3: Implement Admin shell**

Render Admin navigation only for safe UX, but keep all Admin data requests server-authorized. Admin overview displays only the allowlisted operational data returned by existing Admin health/overview APIs.

- [ ] **Step 4: Run tests**

Run: `cd web-client && npm test -- AdminRoute AdminOverviewPage`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web-client/src/admin
git commit -m "feat(web): add administrator workspace"
```

### Task 2: Build staff and account administration

**Files:**
- Create: `web-client/src/admin/staff/StaffAccountsPage.tsx`
- Create: `web-client/src/admin/staff/AccountEditor.tsx`
- Create: `web-client/src/admin/staff/TemporaryPinDialog.tsx`
- Create/Test: `web-client/src/admin/staff/AccountEditor.test.tsx`
- Extend: `backend/webapp/web_api/admin.py`

**Interfaces:**
- Consumes: existing Admin staff/account creation, role assignment, reset, deactivate/reactivate operations.
- Produces: roster-first account management and one-time PIN presentation.

- [ ] **Step 1: Write failing one-time PIN tests**

```tsx
it("shows a reset pin once and does not refetch it", async () => {
  render(<AccountEditor />);
  await resetPinFor("1001");
  expect(await screen.findByText(/temporary pin/i)).toBeVisible();
  await userEvent.click(screen.getByRole("button", {name: /close/i}));
  expect(screen.queryByText(/temporary pin/i)).toBeNull();
});
```

- [ ] **Step 2: Run tests**

Run: `cd web-client && npm test -- AccountEditor`
Expected: FAIL.

- [ ] **Step 3: Implement account management**

Require an approved staff identity when creating accounts. Role is `officer` or `admin`. Temporary/reset PIN values live only in component memory for the current response and disappear after dismissal/navigation. Deactivation confirmation explains that report/audit history is retained.

- [ ] **Step 4: Run frontend and Admin account suites**

Run: `cd web-client && npm test -- AccountEditor && cd .. && python -m pytest tests/integration/test_admin_api.py tests/integration/test_account_creation.py tests/integration/test_admin_session_revocation.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web-client/src/admin/staff backend/webapp/web_api/admin.py
git commit -m "feat(web): add staff and account administration"
```

### Task 3: Add reusable Admin PIN step-up dialog

**Files:**
- Create: `web-client/src/admin/security/AdminStepUpDialog.tsx`
- Create: `web-client/src/admin/security/useAdminStepUp.ts`
- Create/Test: `web-client/src/admin/security/AdminStepUpDialog.test.tsx`

**Interfaces:**
- Consumes: browser adapter for the existing `admin-step-up` operation with a concrete `purpose`.
- Produces: `ensureAdminStepUp(purpose): Promise<void>`.

- [ ] **Step 1: Write failing step-up test**

```tsx
it("requests the admin pin only for the requested sensitive purpose", async () => {
  const {ensureAdminStepUp} = renderStepUpHook();
  await act(() => ensureAdminStepUp("account.reset_pin"));
  expect(screen.getByText(/confirm administrator pin/i)).toBeVisible();
});
```

- [ ] **Step 2: Run focused test**

Run: `cd web-client && npm test -- AdminStepUpDialog`
Expected: FAIL.

- [ ] **Step 3: Implement step-up**

Never cache the PIN. Cache only the safe server-issued elevation expiration/purpose in React memory. If a sensitive API returns step-up-required, open the dialog for that exact purpose then retry the idempotent mutation once.

- [ ] **Step 4: Run tests and backend elevation tests**

Run: `cd web-client && npm test -- AdminStepUpDialog && cd .. && python -m pytest tests/unit/test_admin_elevation.py tests/integration/test_admin_step_up.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web-client/src/admin/security
git commit -m "feat(web): add administrator step-up"
```

### Task 4: Build All Reports and attributed Admin editing

**Files:**
- Create: `web-client/src/admin/reports/AllReportsPage.tsx`
- Create: `web-client/src/admin/reports/AdminReportDetailPage.tsx`
- Create: `web-client/src/admin/reports/AdminRevisionEditor.tsx`
- Create/Test: `web-client/src/admin/reports/AdminRevisionEditor.test.tsx`
- Extend: `backend/webapp/web_api/admin_reports.py`

**Interfaces:**
- Consumes: Admin report search/detail/edit/reopen/restore/transfer APIs.
- Produces: server-paginated organization-wide report search and revisioned edits.

- [ ] **Step 1: Write failing attributed-edit test**

```tsx
it("shows the newly attributed revision after an admin edit", async () => {
  render(<AdminReportDetailPage />);
  await editNarrative("Corrected text");
  await saveAdminRevision();
  expect(await screen.findByText(/edited by administrator/i)).toBeVisible();
  expect(screen.getByText(/revision 3/i)).toBeVisible();
});
```

- [ ] **Step 2: Run tests**

Run: `cd web-client && npm test -- AdminRevisionEditor`
Expected: FAIL.

- [ ] **Step 3: Implement Admin report surfaces**

Use server-side search filters/pagination. Include current revision in mutations; show `409` conflicts rather than overwriting. Reopen/restore/transfer actions use Admin step-up when the API requires it. Display original owner separately from acting editor.

- [ ] **Step 4: Run frontend and Admin report suites**

Run: `cd web-client && npm test -- AdminRevisionEditor && cd .. && python -m pytest tests/integration/test_admin_report_api.py tests/integration/test_admin_report_search.py tests/integration/test_admin_bulk_export.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web-client/src/admin/reports backend/webapp/web_api/admin_reports.py
git commit -m "feat(web): add administrator report oversight"
```

### Task 5: Add audit, health, and bulk export surfaces

**Files:**
- Create: `web-client/src/admin/audit/AuditPage.tsx`
- Create: `web-client/src/admin/health/SystemHealthPage.tsx`
- Create: `web-client/src/admin/reports/BulkExportPanel.tsx`
- Create/Test: `web-client/src/admin/audit/AuditPage.test.tsx`
- Extend: `backend/webapp/web_api/admin_audit.py`, `admin_health.py`

**Interfaces:**
- Consumes: allowlisted Admin audit/health and bulk export APIs.
- Produces: paginated audit view, safe health status, authorized export flow.

- [ ] **Step 1: Write failing audit redaction test**

```tsx
it("renders only allowlisted audit fields returned by the server", async () => {
  render(<AuditPage />);
  expect(await screen.findByText(/report.updated/i)).toBeVisible();
  expect(screen.queryByText(/raw question/i)).toBeNull();
});
```

- [ ] **Step 2: Run tests**

Run: `cd web-client && npm test -- AuditPage SystemHealthPage`
Expected: FAIL.

- [ ] **Step 3: Implement Admin operational views**

Do not add new raw logging or expose internal exception text. Display the server's existing safe health categories and fixed audit schema. Bulk export works from server-selected report IDs/query criteria and never reconstructs a ZIP client-side from cached reports.

- [ ] **Step 4: Run frontend and backend operational tests**

Run: `cd web-client && npm test -- AuditPage SystemHealthPage && cd .. && python -m pytest tests/integration/test_admin_audit_health.py tests/integration/test_admin_bulk_export.py tests/security/test_sensitive_logging.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web-client/src/admin/audit web-client/src/admin/health web-client/src/admin/reports/BulkExportPanel.tsx backend/webapp/web_api/admin_audit.py backend/webapp/web_api/admin_health.py
git commit -m "feat(web): add admin audit health and exports"
```

### Task 6: Administrator E2E acceptance

**Files:**
- Create: `web-client/e2e/admin.spec.ts`

**Interfaces:**
- Produces: one complete fictional Admin acceptance journey.

- [ ] **Step 1: Write the E2E test**

Test flow: Admin signs in; creates an Officer account from fictional roster; sees one-time PIN; resets PIN; deactivates/reactivates account; searches another Officer's report; edits it and verifies a new attributed revision; exercises required step-up; views audit/health; performs authorized export; signs out.

- [ ] **Step 2: Run E2E and confirm missing wiring fails**

Run: `cd web-client && npm run test:e2e -- admin.spec.ts`
Expected: FAIL until all Admin surfaces are connected.

- [ ] **Step 3: Fix only acceptance defects revealed by the E2E test**

Do not add unrelated Admin features. Preserve existing server authorization and audit semantics.

- [ ] **Step 4: Run full Admin/client/backend suite**

Run: `cd web-client && npm test && npm run build && npm run test:e2e -- admin.spec.ts && cd .. && python -m pytest tests/contract tests/integration/test_admin_api.py tests/integration/test_admin_report_api.py tests/integration/test_admin_audit_health.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web-client/e2e/admin.spec.ts web-client/src/admin backend/webapp/web_api
git commit -m "feat(web): complete administrator web parity"
```
