import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { Page, Route } from "@playwright/test";

const PROFILE = {
  account_id: "00000000-0000-4000-8000-000000000001",
  staff_id: "00000000-0000-4000-8000-000000000002",
  session_id: "00000000-0000-4000-8000-000000000003",
  employee_number: "F-1001",
  display_name: "Officer Casey Morgan",
  rank: "Officer",
  shift: "A",
  role: "user",
  must_change_pin: false,
} as const;

const INCIDENT = {
  incident_id: "00000000-0000-4000-8000-000000000010",
  incident_number: "2026-08-029",
  incident_name: "Fictional Training Incident",
  incident_date: "2026-08-19",
  category: "training",
  location: "Training Hall",
  reporting_officers: [{
    staff_id: PROFILE.staff_id,
    display_name: PROFILE.display_name,
  }],
  relationship: "reporting",
  progress: {
    code: "ready_to_review",
    label: "Ready to review",
    blocking_count: 0,
  },
  officer_report_count: 1,
  required_paperwork_count: 3,
  updated_at: "2026-08-19T19:00:00Z",
} as const;

const DIGITAL_FORM = {
  template_id: "00000000-0000-4000-8000-000000000020",
  code: "medical_documentation_checklist",
  name: "Medical Documentation Checklist",
  category: "medical",
  purpose: "Approved digital medical documentation checklist.",
  when_used: "Use when medical evaluation or treatment is documented.",
  output_kind: "digital_document",
  revision_label: "Current approved revision",
  capabilities: [
    "preview",
    "print",
    "download_pdf",
    "fillable",
    "blank",
    "attach_to_incident",
  ],
  frequent: true,
  obtain_from: null,
} as const;

const PHYSICAL_FORM = {
  template_id: "00000000-0000-4000-8000-000000000021",
  code: "chain_of_custody_physical",
  name: "Chain of Custody",
  category: "evidence",
  purpose: "Official physical carbon-copy evidence form.",
  when_used: "Use when evidence custody is transferred.",
  output_kind: "physical_only",
  revision_label: "Current approved revision",
  capabilities: ["attach_to_incident", "physical_guidance"],
  frequent: true,
  obtain_from: "Approved forms location",
} as const;

const STRUCTURE = JSON.parse(
  readFileSync(
    resolve(process.cwd(), "../../templates/paperwork/count_sheet.json"),
    "utf-8",
  ),
) as {
  schema_version: 1;
  title: string;
  columns: string[];
  areas: string[];
  operational_fields: string[];
  attachment_reminders: string[];
};

interface CountRecord {
  record_id: string;
  kind: "count_sheet";
  work_date: string;
  shift: string | null;
  current_revision_number: number;
  payload: {
    schema_version: 1;
    count_started: string | null;
    count_ended: string | null;
    cells: Record<string, Record<string, number | null>>;
    in_housing: Record<string, number | null>;
    operational: Record<string, number | null>;
  };
  validation: ReturnType<typeof totals>;
  created_by_staff_member_id: string;
  last_editor_staff_member_id: string;
  created_at: string;
  updated_at: string;
}

export interface OfficerApiState {
  countRecord: CountRecord | null;
  policyQuestions: string[];
  sessions: Array<{
    session_id: string;
    device_label: string;
    persistent: boolean;
    created_at: string;
    last_seen_at: string;
    expires_at: string;
    current: boolean;
  }>;
}

function numeric(value: number | null | undefined): number {
  return value ?? 0;
}

function totals(payload: CountRecord["payload"]) {
  const row_totals: Record<string, number> = {};
  for (const area of STRUCTURE.areas) {
    row_totals[area] = STRUCTURE.columns.reduce(
      (sum, column) => sum + numeric(payload.cells[area]?.[column]),
      0,
    );
  }
  const out_of_housing: Record<string, number> = {};
  const unit_totals: Record<string, number> = {};
  for (const column of STRUCTURE.columns) {
    out_of_housing[column] = STRUCTURE.areas.reduce(
      (sum, area) => sum + numeric(payload.cells[area]?.[column]),
      0,
    );
    unit_totals[column] = out_of_housing[column] + numeric(payload.in_housing[column]);
  }
  const housing_total = Object.values(unit_totals).reduce((sum, value) => sum + value, 0);
  const operational_total = STRUCTURE.operational_fields.reduce(
    (sum, field) => sum + numeric(payload.operational[field]),
    0,
  );
  const difference = housing_total - operational_total;
  return {
    row_totals,
    out_of_housing,
    unit_totals,
    column_totals: { ...unit_totals },
    housing_total,
    operational_total,
    difference,
    reconciled: difference === 0,
  };
}

function detail<T extends object>(item: T): T & { definition: Record<string, unknown> } {
  return { ...item, definition: {} };
}

async function fulfill(route: Route, data: unknown, status = 200): Promise<void> {
  await route.fulfill({
    status,
    contentType: "application/json",
    headers: { "X-Request-ID": "e2e-request" },
    body: JSON.stringify({ data, request_id: "e2e-request" }),
  });
}

async function fail(
  route: Route,
  code: string,
  message: string,
  status: number,
): Promise<void> {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify({
      error: { code, message, retryable: false, details: {} },
      request_id: "e2e-request",
    }),
  });
}

export async function installOfficerApi(page: Page): Promise<OfficerApiState> {
  const state: OfficerApiState = {
    countRecord: null,
    policyQuestions: [],
    sessions: [
      {
        session_id: PROFILE.session_id,
        device_label: "Current browser",
        persistent: false,
        created_at: "2026-08-19T17:00:00Z",
        last_seen_at: "2026-08-19T19:00:00Z",
        expires_at: "2026-09-18T17:00:00Z",
        current: true,
      },
      {
        session_id: "00000000-0000-4000-8000-000000000004",
        device_label: "Training laptop",
        persistent: true,
        created_at: "2026-08-18T12:00:00Z",
        last_seen_at: "2026-08-19T16:00:00Z",
        expires_at: "2026-09-17T12:00:00Z",
        current: false,
      },
    ],
  };

  await page.context().addCookies([{
    name: "slut_web_csrf",
    value: "e2e-csrf-token",
    url: "http://127.0.0.1:4173/",
  }]);

  await page.route("**/api/web/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace("/api/web/v1", "");
    const method = request.method();

    if (path === "/auth/session" && method === "GET") {
      await fulfill(route, { authenticated: true, profile: PROFILE });
      return;
    }
    if (path === "/auth/renew" && method === "POST") {
      await fulfill(route, { authenticated: true, profile: PROFILE });
      return;
    }
    if (path === "/auth/logout" && method === "POST") {
      await fulfill(route, { signed_out: true });
      return;
    }
    if (path === "/home" && method === "GET") {
      await fulfill(route, {
        continue_incident: INCIDENT,
        recent_incidents: [INCIDENT],
        quick_forms: [
          {
            template_id: DIGITAL_FORM.template_id,
            code: DIGITAL_FORM.code,
            name: DIGITAL_FORM.name,
            output_kind: DIGITAL_FORM.output_kind,
          },
          {
            template_id: PHYSICAL_FORM.template_id,
            code: PHYSICAL_FORM.code,
            name: PHYSICAL_FORM.name,
            output_kind: PHYSICAL_FORM.output_kind,
          },
        ],
        count_sheet: state.countRecord
          ? {
              record_id: state.countRecord.record_id,
              current_revision_number: state.countRecord.current_revision_number,
              updated_at: state.countRecord.updated_at,
            }
          : null,
      });
      return;
    }
    if (path === "/paperwork/count-sheets/structure" && method === "GET") {
      await fulfill(route, STRUCTURE);
      return;
    }
    if (path === "/paperwork" && method === "GET") {
      await fulfill(route, {
        items: state.countRecord
          ? [{
              ...state.countRecord,
              payload: undefined,
              validation: {
                housing_total: state.countRecord.validation.housing_total,
                operational_total: state.countRecord.validation.operational_total,
                difference: state.countRecord.validation.difference,
                reconciled: state.countRecord.validation.reconciled,
              },
            }]
          : [],
        next_cursor: null,
      });
      return;
    }
    if (path === "/paperwork/count-sheets" && method === "POST") {
      const body = request.postDataJSON() as Omit<CountRecord, "record_id"> & {
        payload: CountRecord["payload"];
        work_date: string;
        shift: string | null;
      };
      const now = "2026-08-19T19:15:00Z";
      state.countRecord = {
        record_id: "00000000-0000-4000-8000-000000000030",
        kind: "count_sheet",
        work_date: body.work_date,
        shift: body.shift,
        current_revision_number: 1,
        payload: body.payload,
        validation: totals(body.payload),
        created_by_staff_member_id: PROFILE.staff_id,
        last_editor_staff_member_id: PROFILE.staff_id,
        created_at: now,
        updated_at: now,
      };
      await fulfill(route, state.countRecord, 201);
      return;
    }
    const countMatch = path.match(/^\/paperwork\/count-sheets\/([0-9a-f-]+)$/i);
    if (countMatch && method === "GET" && state.countRecord) {
      await fulfill(route, state.countRecord);
      return;
    }
    if (countMatch && method === "PATCH" && state.countRecord) {
      const body = request.postDataJSON() as { payload: CountRecord["payload"]; work_date: string; shift: string | null };
      state.countRecord = {
        ...state.countRecord,
        work_date: body.work_date,
        shift: body.shift,
        current_revision_number: state.countRecord.current_revision_number + 1,
        payload: body.payload,
        validation: totals(body.payload),
        updated_at: "2026-08-19T19:20:00Z",
      };
      await fulfill(route, state.countRecord);
      return;
    }
    if (path.match(/^\/paperwork\/count-sheets\/[0-9a-f-]+\/actions$/i) && method === "POST" && state.countRecord) {
      const body = request.postDataJSON() as { action: "preview" | "print" | "download_pdf" };
      await fulfill(route, {
        recorded: true,
        record_id: state.countRecord.record_id,
        kind: "count_sheet",
        revision_number: state.countRecord.current_revision_number,
        action: body.action,
      });
      return;
    }
    if (path === "/forms" && method === "GET") {
      await fulfill(route, {
        items: [DIGITAL_FORM, PHYSICAL_FORM],
        categories: ["evidence", "medical"],
        next_cursor: null,
      });
      return;
    }
    if (path === "/forms/selection/preview" && method === "POST") {
      const ids = (request.postDataJSON() as { template_ids: string[] }).template_ids;
      const selected = [DIGITAL_FORM, PHYSICAL_FORM].filter((item) => ids.includes(item.template_id));
      await fulfill(route, {
        items: selected.map(detail),
        digital_items: selected.filter((item) => item.output_kind === "digital_document").map(detail),
        physical_items: selected.filter((item) => item.output_kind === "physical_only").map(detail),
      });
      return;
    }
    if (path === "/forms/selection/download" && method === "POST") {
      const ids = (request.postDataJSON() as { template_ids: string[] }).template_ids;
      const selected = [DIGITAL_FORM, PHYSICAL_FORM].filter((item) => ids.includes(item.template_id));
      await fulfill(route, {
        downloadable_items: selected.filter((item) => item.output_kind === "digital_document").map(detail),
        skipped_physical_items: selected.filter((item) => item.output_kind === "physical_only").map(detail),
      });
      return;
    }
    if (path === "/policy/questions" && method === "POST") {
      const body = request.postDataJSON() as { question: string };
      state.policyQuestions.push(body.question);
      await fulfill(route, {
        answer: "Fictional policy requires documented supervisory review [1].",
        citations: [{
          title: "Fictional Operations Policy",
          location: "Source passage 1",
          excerpt: "A supervisory review is documented before closure.",
        }],
      });
      return;
    }
    if (path === "/account/sessions" && method === "GET") {
      await fulfill(route, { items: state.sessions });
      return;
    }
    const sessionMatch = path.match(/^\/account\/sessions\/([0-9a-f-]+)$/i);
    if (sessionMatch && method === "DELETE") {
      state.sessions = state.sessions.filter((item) => item.session_id !== sessionMatch[1]);
      await fulfill(route, { session_id: sessionMatch[1], revoked: true });
      return;
    }
    if (path === "/account/change-pin" && method === "POST") {
      await fulfill(route, { changed: true, session_id: PROFILE.session_id, must_change_pin: false });
      return;
    }
    if (path === "/account/logout-all" && method === "POST") {
      state.sessions = [];
      await fulfill(route, { signed_out: true, session_count: 2 });
      return;
    }

    await fail(route, "not_found", `No E2E route is defined for ${method} ${path}.`, 404);
  });

  return state;
}
