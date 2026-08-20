import type { Page, Route } from "@playwright/test";
import perimeterTemplate from "../../../../../templates/paperwork/daily/perimeter_check.json" with { type: "json" };

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

const OFFICER = {
  staff_id: "00000000-0000-4000-8000-000000000920",
  employee_number: "F-1001",
  display_name: "Officer Casey Morgan",
  rank: "Officer",
  shift: "A",
} as const;

const PREPARER = {
  staff_id: "00000000-0000-4000-8000-000000000921",
  employee_number: "F-1002",
  display_name: "Officer Riley Stone",
  rank: "Officer",
  shift: "A",
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
  reporting_officers: [{ staff_id: OFFICER.staff_id, display_name: OFFICER.display_name }],
  preparers: [{ staff_id: PREPARER.staff_id, display_name: PREPARER.display_name }],
  last_editor: { staff_id: OFFICER.staff_id, display_name: OFFICER.display_name },
  progress: { code: "ready_to_review", label: "Ready to review", blocking_count: 0 },
  officer_report_count: 1,
  required_paperwork_count: 0,
  created_at: "2026-08-19T16:00:00Z",
  updated_at: "2026-08-19T19:00:00Z",
} as const;

const REPORT = {
  report_id: "00000000-0000-4000-8000-000000000925",
  incident_id: INCIDENT.incident_id,
  report_type: "officer_report",
  presentation: "document",
  allowed_actions: ["edit", "print", "download_docx"],
  status: "draft",
  current_revision_number: 2,
  reporting_officer: OFFICER,
  preparer: PREPARER,
  updated_at: "2026-08-19T19:00:00Z",
} as const;

type DailyKind =
  | "assignment_roster"
  | "uniform_inspection"
  | "metal_detector_test"
  | "perimeter_check"
  | "random_search_log"
  | "detector_sign_out";

interface MockDailyRecord {
  record_id: string;
  kind: DailyKind;
  title: string;
  work_date: string;
  shift: string;
  revision: number;
  current_revision_number: number;
  state: "saved" | "needs_attention";
  warning_count: number;
  validation: Record<string, unknown>;
  created_by_staff_member_id: string;
  last_editor_staff_member_id: string;
  created_at: string;
  updated_at: string;
  payload: Record<string, unknown>;
  template: {
    schema_version: 1;
    title: string;
    print_orientation: "portrait" | "landscape";
    definition: Record<string, unknown>;
  };
}

const DAILY_PRESENTATION: Record<DailyKind, { title: string; orientation: "portrait" | "landscape" }> = {
  assignment_roster: { title: "Shift Assignment Roster", orientation: "landscape" },
  uniform_inspection: { title: "Uniform Inspection Log", orientation: "landscape" },
  metal_detector_test: { title: "Daily Walk-Through Metal Detector Testing", orientation: "landscape" },
  perimeter_check: { title: "Perimeter Check List", orientation: "portrait" },
  random_search_log: { title: "Random Searches Log", orientation: "landscape" },
  detector_sign_out: { title: "Handheld Metal Detector Sign-Out", orientation: "portrait" },
};

const DAILY_KIND_PATTERN = "assignment_roster|uniform_inspection|metal_detector_test|perimeter_check|random_search_log|detector_sign_out";

const MONTHLY_PRINT_TEMPLATES = [
  { code: "monthly_windows_bars_doors", title: "Windows, Bars & Doors Check Log", period: "monthly", category: "security_checks", schema_version: 1, page_size: "letter", orientation: "landscape", definition: { columns: ["Date", "Exterior Bks. Windows", "All Inmate Housing Windows", "Housing Doors", "All Cell Bars", "Officer's Signature"], footer_note: "All bars will be checked with a rubber mallet." } },
  { code: "monthly_chemical_agents", title: "Use of Chemical Agents Log", period: "monthly", category: "security_checks", schema_version: 1, page_size: "letter", orientation: "landscape", definition: { columns: ["Date", "Staff", "Inmate Name / #", "Conforms To Policy", "Medical Attention", "Supervisor"] } },
  { code: "monthly_contraband_standard", title: "Contraband Search Log — Standard Area Rotation", period: "monthly", category: "security_checks", schema_version: 1, page_size: "letter", orientation: "landscape", definition: { columns: ["Date/Time", "Area Searched", "Contraband Found", "Searching Officers", "Disposition of Contraband"], schedule: ["Gym", "School", "Front Office / Barber Shop", "Boiler Room", "Kitchen and ODR", "Laundry Press Area / Main Showers"] } },
  { code: "monthly_contraband_expanded", title: "Contraband Search Log — Expanded Area Rotation", period: "monthly", category: "security_checks", schema_version: 1, page_size: "letter", orientation: "landscape", definition: { columns: ["Date/Time", "Area Searched", "Contraband Found", "Searching Officers", "Disposition of Contraband"], schedule: ["Gym", "Chapel", "Entrance Building", "School", "Front Office / Barbershop", "Boiler Room", "Kitchen / ODR", "Laundry", "Inmate Barbershop", "Inside Maintenance"] } },
] as const;

function dailySummary(record: MockDailyRecord): Omit<MockDailyRecord, "payload" | "template"> {
  const { payload: _payload, template: _template, ...summary } = record;
  return summary;
}

function incidentRecord() {
  return {
    incident_id: INCIDENT.incident_id,
    incident_number: INCIDENT.incident_number,
    incident_name: INCIDENT.incident_name,
    status: INCIDENT.records_status,
    current_revision_number: 4,
    reporting_staff_ids: [OFFICER.staff_id],
    reporting_officers: [OFFICER],
    field_notes: "Fictional training notes used only for browser verification.",
    incident_date: INCIDENT.incident_date,
    incident_time: "18:20:00",
    facility: INCIDENT.facility,
    shift: INCIDENT.shift,
    location: INCIDENT.location,
    category: INCIDENT.category,
    classification: { category: "training" },
    extracted_facts: { location: "Training Hall" },
    gap_answers: {},
    charges: [],
    validation: {},
    warnings: [],
    created_at: INCIDENT.created_at,
    updated_at: INCIDENT.updated_at,
  };
}

function adminIncidentDetail() {
  return {
    incident_id: INCIDENT.incident_id,
    incident_number: INCIDENT.incident_number,
    incident_name: INCIDENT.incident_name,
    records_status: INCIDENT.records_status,
    current_revision_number: 4,
    reporting_staff_ids: [OFFICER.staff_id],
    reporting_officers: [OFFICER],
    preparers: [PREPARER],
    reports: [{
      report_id: REPORT.report_id,
      report_type: REPORT.report_type,
      status: REPORT.status,
      current_revision_number: REPORT.current_revision_number,
      reporting_officer: OFFICER,
      preparer: PREPARER,
      updated_at: REPORT.updated_at,
    }],
    field_notes: "Fictional training notes used only for browser verification.",
    incident_date: INCIDENT.incident_date,
    incident_time: "18:20:00",
    facility: INCIDENT.facility,
    shift: INCIDENT.shift,
    location: INCIDENT.location,
    category: INCIDENT.category,
    classification: { category: "training" },
    extracted_facts: { location: "Training Hall" },
    gap_answers: {},
    charges: [],
    validation: {},
    created_at: INCIDENT.created_at,
    updated_at: INCIDENT.updated_at,
    admin_attribution_required: true,
  };
}

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
  const dailyRecords = new Map<string, MockDailyRecord>();
  let dailySequence = 970;

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
          assignment_roster: { status: "not_started", state: "not_started", record_id: null, revision: null, warning_count: 0, shift: null, updated_at: null },
          uniform_inspection: { status: "saved", state: "saved", record_id: "00000000-0000-4000-8000-000000000930", revision: 1, warning_count: 0, shift: "A", updated_at: "2026-08-19T18:30:00Z" },
        },
        incidents_needing_attention: [{
          incident_id: INCIDENT.incident_id,
          incident_number: INCIDENT.incident_number,
          incident_name: INCIDENT.incident_name,
          progress: INCIDENT.progress,
          report_count: 1,
          required_paperwork_count: 0,
          updated_at: INCIDENT.updated_at,
        }],
        account_conditions: { locked: 1, deactivated: 2, temporary_pin: 1 },
        system_availability: { database: "Operational", queue: "Operational", ai: "Operational", policy_expert: "Operational", backup_restore: "Unavailable" },
        recent_administrative_activity: [{ event_id: "00000000-0000-4000-8000-000000000940", action: "admin.staff_updated", target_type: "staff_member", target_id: OFFICER.staff_id, result: "success", occurred_at: "2026-08-19T19:10:00Z" }],
      });
      return;
    }
    if (path === "/admin/incidents" && method === "GET") {
      await fulfill(route, { items: [INCIDENT], next_cursor: null });
      return;
    }
    if (path === "/print-templates" && method === "GET") {
      await fulfill(route, { items: url.searchParams.get("period") === "monthly" ? MONTHLY_PRINT_TEMPLATES : [] });
      return;
    }
    if (path === "/print-templates/actions" && method === "POST") {
      await fulfill(route, { recorded: true });
      return;
    }
    if (path === "/admin/paperwork/daily" && method === "GET") {
      const workDate = url.searchParams.get("work_date");
      const shift = url.searchParams.get("shift");
      const items = [...dailyRecords.values()]
        .filter((record) => record.work_date === workDate && record.shift === shift)
        .map(dailySummary);
      await fulfill(route, { items, next_cursor: null });
      return;
    }
    if (path === "/admin/paperwork/daily/perimeter_check/template" && method === "GET") {
      await fulfill(route, perimeterTemplate);
      return;
    }
    const dailyCreateMatch = path.match(new RegExp(`^/admin/paperwork/daily/(${DAILY_KIND_PATTERN})$`));
    if (dailyCreateMatch && method === "POST") {
      const kind = dailyCreateMatch[1] as DailyKind;
      const body = JSON.parse(request.postData() ?? "{}") as {
        work_date?: string;
        shift?: string;
        payload?: Record<string, unknown>;
      };
      dailySequence += 1;
      const recordId = `00000000-0000-4000-8000-${String(dailySequence).padStart(12, "0")}`;
      const presentation = DAILY_PRESENTATION[kind];
      const now = "2026-08-20T15:00:00Z";
      const record: MockDailyRecord = {
        record_id: recordId,
        kind,
        title: presentation.title,
        work_date: body.work_date ?? "2026-08-20",
        shift: body.shift ?? "D",
        revision: 1,
        current_revision_number: 1,
        state: "saved",
        warning_count: 0,
        validation: {},
        created_by_staff_member_id: ADMIN.staff_id,
        last_editor_staff_member_id: ADMIN.staff_id,
        created_at: now,
        updated_at: now,
        payload: body.payload ?? {},
        template: {
          schema_version: 1,
          title: presentation.title,
          print_orientation: presentation.orientation,
          definition: {},
        },
      };
      dailyRecords.set(recordId, record);
      await fulfill(route, record, 201);
      return;
    }
    const dailyActionMatch = path.match(new RegExp(`^/admin/paperwork/daily/(${DAILY_KIND_PATTERN})/([^/]+)/(actions|revisions)$`));
    if (dailyActionMatch && dailyActionMatch[3] === "actions" && method === "POST") {
      await fulfill(route, { recorded: true });
      return;
    }
    if (dailyActionMatch && dailyActionMatch[3] === "revisions" && method === "GET") {
      const record = dailyRecords.get(dailyActionMatch[2]);
      await fulfill(route, {
        items: record ? [{
          revision_number: record.revision,
          reason: "manual_save",
          changed_fields: ["payload"],
          editor_staff_member_id: ADMIN.staff_id,
          client_version: "0.1.0-e2e",
          created_at: record.updated_at,
        }] : [],
        next_cursor: null,
      });
      return;
    }
    const dailyRecordMatch = path.match(new RegExp(`^/admin/paperwork/daily/(${DAILY_KIND_PATTERN})/([^/]+)$`));
    if (dailyRecordMatch && method === "GET") {
      const record = dailyRecords.get(dailyRecordMatch[2]);
      await fulfill(route, record ?? {}, record ? 200 : 404);
      return;
    }
    if (dailyRecordMatch && method === "PATCH") {
      const record = dailyRecords.get(dailyRecordMatch[2]);
      if (!record) {
        await fulfill(route, {}, 404);
        return;
      }
      const body = JSON.parse(request.postData() ?? "{}") as { payload?: Record<string, unknown> };
      const revision = record.revision + 1;
      const saved: MockDailyRecord = {
        ...record,
        revision,
        current_revision_number: revision,
        payload: body.payload ?? record.payload,
        updated_at: "2026-08-20T15:05:00Z",
      };
      dailyRecords.set(saved.record_id, saved);
      await fulfill(route, saved);
      return;
    }
    if (path === `/admin/incidents/${INCIDENT.incident_id}` && method === "GET") {
      await fulfill(route, adminIncidentDetail());
      return;
    }
    if (path === `/admin/incidents/${INCIDENT.incident_id}/records-status` && method === "PATCH") {
      const body = JSON.parse(request.postData() ?? "{}") as { records_status?: string };
      await fulfill(route, { ...adminIncidentDetail(), records_status: body.records_status ?? INCIDENT.records_status, current_revision_number: 5 });
      return;
    }
    if (path === "/admin/staff" && method === "GET") {
      await fulfill(route, {
        items: [{
          staff_id: OFFICER.staff_id,
          employee_number: OFFICER.employee_number,
          rank: OFFICER.rank,
          first_name: "Casey",
          last_name: "Morgan",
          display_name: OFFICER.display_name,
          shift: OFFICER.shift,
          is_active: true,
          account: {
            account_id: "00000000-0000-4000-8000-000000000950",
            staff_id: OFFICER.staff_id,
            employee_number: OFFICER.employee_number,
            display_name: OFFICER.display_name,
            role: "user",
            status: "active",
            must_change_pin: false,
            created_at: "2026-08-18T10:00:00Z",
            updated_at: "2026-08-19T18:00:00Z",
          },
          created_at: "2026-08-18T10:00:00Z",
          updated_at: "2026-08-19T18:00:00Z",
        }, {
          staff_id: PREPARER.staff_id,
          employee_number: PREPARER.employee_number,
          rank: PREPARER.rank,
          first_name: "Riley",
          last_name: "Stone",
          display_name: PREPARER.display_name,
          shift: PREPARER.shift,
          is_active: true,
          account: null,
          created_at: "2026-08-18T10:00:00Z",
          updated_at: "2026-08-19T18:00:00Z",
        }],
        next_cursor: null,
      });
      return;
    }
    if (path === "/admin/accounts/00000000-0000-4000-8000-000000000950/sessions" && method === "GET") {
      await fulfill(route, {
        items: [{
          session_id: "00000000-0000-4000-8000-000000000960",
          device_label: "Training laptop",
          persistent: true,
          last_used_at: "2026-08-19T19:05:00Z",
          created_at: "2026-08-19T17:00:00Z",
          access_expires_at: "2099-08-20T02:00:00Z",
          renewal_expires_at: "2099-09-20T02:00:00Z",
          revoked_at: null,
          revoke_reason: null,
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
          target_id: OFFICER.staff_id,
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
      await fulfill(route, { account_id: "00000000-0000-4000-8000-000000000950", revoked_session_ids: ["00000000-0000-4000-8000-000000000960"], revoked_count: 1 });
      return;
    }
    if (path.startsWith("/admin/accounts/") && method === "PATCH") {
      await fulfill(route, {});
      return;
    }
    if (path.startsWith("/admin/staff/") && method === "PATCH") {
      await fulfill(route, {});
      return;
    }

    if (path === `/incidents/${INCIDENT.incident_id}` && method === "GET") {
      await fulfill(route, incidentRecord());
      return;
    }
    if (path === `/incidents/${INCIDENT.incident_id}/reports` && method === "GET") {
      await fulfill(route, { items: [REPORT] });
      return;
    }
    if (path === `/incidents/${INCIDENT.incident_id}/packet` && method === "GET") {
      await fulfill(route, { items: [] });
      return;
    }

    await fulfill(route, {}, 200);
  });
}
