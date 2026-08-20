import type { Page, Route } from "@playwright/test";

const ADMIN = {
  account_id: "00000000-0000-4000-8000-000000000901",
  staff_id: "00000000-0000-4000-8000-000000000902",
  session_id: "00000000-0000-4000-8000-000000000903",
  employee_number: "A-9001",
  display_name: "Captain Jordan Blake",
  rank: "Captain",
  shift: "A",
  role: "admin",
  must_change_pin: false,
} as const;

const INCIDENT = {
  incident_id: "00000000-0000-4000-8000-000000000910",
  incident_number: "2026-08-029",
  incident_name: "Fictional Training Incident",
  incident_date: "2026-08-19",
  category: "training",
  facility: "North Central Unit",
  location: "Training Hall",
  shift: "A",
  records_status: "in_progress",
  reporting_officers: [{ staff_id: "00000000-0000-4000-8000-000000000920", display_name: "Officer Casey Morgan" }],
  preparers: [{ staff_id: "00000000-0000-4000-8000-000000000921", display_name: "Officer Riley Stone" }],
  last_editor: { staff_id: "00000000-0000-4000-8000-000000000920", display_name: "Officer Casey Morgan" },
  progress: { code: "ready_to_review", label: "Ready to review", blocking_count: 0 },
  officer_report_count: 2,
  required_paperwork_count: 4,
  created_at: "2026-08-19T16:00:00Z",
  updated_at: "2026-08-19T19:00:00Z",
} as const;

async function fulfill(route: Route, data: unknown, status = 200): Promise<void> {
  await route.fulfill({
    status,
    contentType: "application/json",
    headers: { "X-Request-ID": "admin-e2e-request" },
    body: JSON.stringify({ data, request_id: "admin-e2e-request" }),
  });
}

export async function installAdminApi(page: Page): Promise<void> {
  let elevated = false;

  await page.context().addCookies([{
    name: "slut_web_csrf",
    value: "admin-e2e-csrf",
    url: "http://127.0.0.1:4173/",
  }]);

  await page.route("**/api/web/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/^\/api\/web\/v1/, "");
    const method = request.method();

    if (path === "/auth/session" && method === "GET") {
      await fulfill(route, { authenticated: true, profile: ADMIN });
      return;
    }
    if (path === "/admin/elevation" && method === "GET") {
      await fulfill(route, { elevated, elevation_expires_at: elevated ? "2099-08-20T02:00:00Z" : null });
      return;
    }
    if (path === "/admin/elevation" && method === "POST") {
      elevated = true;
      await fulfill(route, { elevated: true, elevation_expires_at: "2099-08-20T02:00:00Z" });
      return;
    }
    if (path === "/admin/step-up" && method === "POST") {
      const body = JSON.parse(request.postData() ?? "{}") as { purpose?: string };
      await fulfill(route, { purpose: body.purpose ?? "unknown", expires_at: "2099-08-20T01:40:00Z" });
      return;
    }
    if (path === "/admin/overview" && method === "GET") {
      await fulfill(route, {
        todays_paperwork: {
          assignment_roster: { status: "not_started", record_id: null, updated_at: null },
          uniform_inspection: { status: "saved", record_id: "00000000-0000-4000-8000-000000000930", updated_at: "2026-08-19T18:30:00Z" },
        },
        incidents_needing_attention: [{
          incident_id: INCIDENT.incident_id,
          incident_number: INCIDENT.incident_number,
          incident_name: INCIDENT.incident_name,
          progress: INCIDENT.progress,
          report_count: 2,
          required_paperwork_count: 4,
          updated_at: INCIDENT.updated_at,
        }],
        account_conditions: { locked: 1, deactivated: 2, temporary_pin: 1 },
        system_availability: { database: "Operational", queue: "Operational", ai: "Operational", policy_expert: "Operational", backup_restore: "Unavailable" },
        recent_administrative_activity: [{ event_id: "00000000-0000-4000-8000-000000000940", action: "admin.staff_updated", target_type: "staff_member", target_id: "00000000-0000-4000-8000-000000000920", result: "success", occurred_at: "2026-08-19T19:10:00Z" }],
      });
      return;
    }
    if (path === "/admin/incidents" && method === "GET") {
      await fulfill(route, { items: [INCIDENT], next_cursor: null });
      return;
    }
    if (path === "/admin/staff" && method === "GET") {
      await fulfill(route, {
        items: [{
          staff_id: "00000000-0000-4000-8000-000000000920",
          employee_number: "F-1001",
          rank: "Officer",
          first_name: "Casey",
          last_name: "Morgan",
          display_name: "Officer Casey Morgan",
          shift: "A",
          is_active: true,
          account: {
            account_id: "00000000-0000-4000-8000-000000000950",
            staff_id: "00000000-0000-4000-8000-000000000920",
            employee_number: "F-1001",
            display_name: "Officer Casey Morgan",
            role: "user",
            status: "active",
            must_change_pin: false,
            created_at: "2026-08-18T10:00:00Z",
            updated_at: "2026-08-19T18:00:00Z",
          },
          created_at: "2026-08-18T10:00:00Z",
          updated_at: "2026-08-19T18:00:00Z",
        }],
        next_cursor: null,
      });
      return;
    }
    if (path === "/admin/audit" && method === "GET") {
      await fulfill(route, {
        items: [{
          event_id: "00000000-0000-4000-8000-000000000940",
          occurred_at: "2026-08-19T19:10:00Z",
          actor_account_id: ADMIN.account_id,
          actor_staff_member_id: ADMIN.staff_id,
          action: "admin.staff_updated",
          target_type: "staff_member",
          target_id: "00000000-0000-4000-8000-000000000920",
          result: "success",
          request_id: "request-fictional-admin-1",
          client_version: "0.1.0",
          details: { changed_fields: ["shift"] },
        }],
        next_cursor: null,
      });
      return;
    }
    if (path === "/admin/health" && method === "GET") {
      await fulfill(route, {
        checked_at: "2026-08-19T19:15:00Z",
        components: { api: "Operational", database: "Operational", ai: "Operational", policy_expert: "Operational", queue: "Operational", backups: "Unavailable" },
        build: { source_commit: "fictional-build", cloud_run_revision: "fictional-revision", alembic_revision: "20260818_0008" },
        notices: [{ component: "backups", status: "Unavailable", message: "Backup restore verification is not exposed in this workspace." }],
      });
      return;
    }
    if (path === "/admin/review-lab-handoffs" && method === "POST") {
      await fulfill(route, { url: "/access-handoff#fictional-one-use-handoff", expires_at: "2099-08-20T01:31:00Z" });
      return;
    }
    if (path.includes("/reset-pin") && method === "POST") {
      await fulfill(route, { account_id: "00000000-0000-4000-8000-000000000950", temporary_pin: "T9R4K2", temporary_pin_expires_at: "2099-08-20T02:00:00Z" });
      return;
    }
    if (path.startsWith("/admin/accounts/") && method === "POST") {
      await fulfill(route, { account_id: "00000000-0000-4000-8000-000000000950", revoked_session_ids: [], revoked_count: 0 });
      return;
    }
    if (path.startsWith("/admin/accounts/") && method === "PATCH") {
      await fulfill(route, {});
      return;
    }

    await fulfill(route, {}, 200);
  });
}
