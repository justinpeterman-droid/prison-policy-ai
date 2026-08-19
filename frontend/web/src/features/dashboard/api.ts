import { webApiRequest } from "../../api/client";

export interface OfficerSummary {
  staffId: string;
  displayName: string;
}

export interface IncidentHomeSummary {
  incidentId: string;
  incidentNumber: string | null;
  incidentName: string | null;
  incidentDate: string | null;
  category: string | null;
  location: string | null;
  reportingOfficers: OfficerSummary[];
  relationship: string;
  progress: {
    code: string;
    label: string;
    blockingCount: number;
  };
  officerReportCount: number;
  requiredPaperworkCount: number;
  updatedAt: string;
}

export interface QuickFormSummary {
  templateId: string;
  code: string;
  name: string;
  outputKind: "digital_document" | "physical_only";
}

export interface CountSheetSummary {
  recordId: string;
  revision: number;
  updatedAt: string;
}

export interface OfficerHomeSummary {
  continueIncident: IncidentHomeSummary | null;
  recentIncidents: IncidentHomeSummary[];
  quickForms: QuickFormSummary[];
  countSheet: CountSheetSummary | null;
  requestPath?: string;
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

function object(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`${label} is invalid.`);
  }
  return value as Record<string, unknown>;
}

function exactKeys(
  value: Record<string, unknown>,
  expected: readonly string[],
  label: string,
): void {
  const keys = Object.keys(value).sort();
  const wanted = [...expected].sort();
  if (keys.length !== wanted.length || keys.some((key, index) => key !== wanted[index])) {
    throw new Error(`${label} has an unsupported field.`);
  }
}

function text(value: unknown, label: string, maximum: number): string {
  if (typeof value !== "string" || !value.trim() || value.length > maximum) {
    throw new Error(`${label} is invalid.`);
  }
  return value.trim();
}

function nullableText(value: unknown, label: string, maximum: number): string | null {
  if (value === null) return null;
  return text(value, label, maximum);
}

function uuid(value: unknown, label: string): string {
  const parsed = text(value, label, 36);
  if (!UUID.test(parsed)) throw new Error(`${label} is invalid.`);
  return parsed;
}

function whole(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0 || value > 100_000) {
    throw new Error(`${label} is invalid.`);
  }
  return value;
}

function timestamp(value: unknown, label: string): string {
  const parsed = text(value, label, 50);
  if (!Number.isFinite(Date.parse(parsed))) throw new Error(`${label} is invalid.`);
  return parsed;
}

function parseOfficer(value: unknown): OfficerSummary {
  const row = object(value, "Reporting officer");
  exactKeys(row, ["staff_id", "display_name"], "Reporting officer");
  return {
    staffId: uuid(row.staff_id, "Staff ID"),
    displayName: text(row.display_name, "Officer name", 200),
  };
}

function parseIncident(value: unknown): IncidentHomeSummary {
  const row = object(value, "Incident summary");
  exactKeys(row, [
    "incident_id",
    "incident_number",
    "incident_name",
    "incident_date",
    "category",
    "location",
    "reporting_officers",
    "relationship",
    "progress",
    "officer_report_count",
    "required_paperwork_count",
    "updated_at",
  ], "Incident summary");
  const rawDate = nullableText(row.incident_date, "Incident date", 10);
  if (rawDate !== null && !ISO_DATE.test(rawDate)) {
    throw new Error("Incident date is invalid.");
  }
  if (!Array.isArray(row.reporting_officers)) {
    throw new Error("Reporting officers are invalid.");
  }
  const progress = object(row.progress, "Incident progress");
  exactKeys(progress, ["code", "label", "blocking_count"], "Incident progress");
  return {
    incidentId: uuid(row.incident_id, "Incident ID"),
    incidentNumber: nullableText(row.incident_number, "Incident number", 11),
    incidentName: nullableText(row.incident_name, "Incident name", 160),
    incidentDate: rawDate,
    category: nullableText(row.category, "Incident category", 120),
    location: nullableText(row.location, "Incident location", 200),
    reportingOfficers: row.reporting_officers.map(parseOfficer),
    relationship: text(row.relationship, "Incident relationship", 40),
    progress: {
      code: text(progress.code, "Progress code", 64),
      label: text(progress.label, "Progress label", 120),
      blockingCount: whole(progress.blocking_count, "Blocking count"),
    },
    officerReportCount: whole(row.officer_report_count, "Report count"),
    requiredPaperworkCount: whole(row.required_paperwork_count, "Paperwork count"),
    updatedAt: timestamp(row.updated_at, "Incident update time"),
  };
}

function parseQuickForm(value: unknown): QuickFormSummary {
  const row = object(value, "Quick form");
  exactKeys(row, ["template_id", "code", "name", "output_kind"], "Quick form");
  const outputKind = row.output_kind;
  if (outputKind !== "digital_document" && outputKind !== "physical_only") {
    throw new Error("Quick form output kind is invalid.");
  }
  return {
    templateId: uuid(row.template_id, "Template ID"),
    code: text(row.code, "Form code", 80),
    name: text(row.name, "Form name", 200),
    outputKind,
  };
}

function parseCountSheet(value: unknown): CountSheetSummary {
  const row = object(value, "Count Sheet summary");
  exactKeys(
    row,
    ["record_id", "current_revision_number", "updated_at"],
    "Count Sheet summary",
  );
  return {
    recordId: uuid(row.record_id, "Count Sheet record ID"),
    revision: whole(row.current_revision_number, "Count Sheet revision"),
    updatedAt: timestamp(row.updated_at, "Count Sheet update time"),
  };
}

export function parseOfficerHomeSummary(value: unknown): OfficerHomeSummary {
  const row = object(value, "Home summary");
  exactKeys(
    row,
    ["continue_incident", "recent_incidents", "quick_forms", "count_sheet"],
    "Home summary",
  );
  if (!Array.isArray(row.recent_incidents) || !Array.isArray(row.quick_forms)) {
    throw new Error("Home summary collections are invalid.");
  }
  return {
    continueIncident: row.continue_incident === null
      ? null
      : parseIncident(row.continue_incident),
    recentIncidents: row.recent_incidents.map(parseIncident),
    quickForms: row.quick_forms.map(parseQuickForm),
    countSheet: row.count_sheet === null ? null : parseCountSheet(row.count_sheet),
  };
}

export async function fetchOfficerHomeSummary(
  recordDate: string,
  shift: string,
): Promise<OfficerHomeSummary> {
  if (!ISO_DATE.test(recordDate) || !shift.trim() || shift.length > 32) {
    throw new Error("Home summary date or shift is invalid.");
  }
  const params = new URLSearchParams({ date: recordDate, shift: shift.trim() });
  const requestPath = `/home?${params.toString()}`;
  const raw = await webApiRequest<unknown>(requestPath);
  return { ...parseOfficerHomeSummary(raw), requestPath };
}
