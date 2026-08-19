import {
  WEB_API_BASE,
  WEB_CLIENT_VERSION,
  readCookie,
  webApiRequest,
} from "../../api/client";

export interface StaffSummary {
  staff_id: string;
  employee_number?: string;
  display_name: string;
  rank?: string | null;
  shift?: string | null;
}

export interface WorkflowProgress {
  code: string;
  label: string;
  blocking_count: number;
}

export interface IncidentSummary {
  incident_id: string;
  incident_number: string | null;
  incident_name: string | null;
  incident_date: string | null;
  category: string | null;
  location: string | null;
  reporting_officers: StaffSummary[];
  relationship: string;
  progress: WorkflowProgress;
  officer_report_count: number;
  required_paperwork_count: number;
  updated_at: string;
}

export interface IncidentPage {
  items: IncidentSummary[];
  next_cursor: string | null;
}

export interface IncidentRecord {
  incident_id: string;
  incident_number: string | null;
  incident_name: string | null;
  status: string;
  current_revision_number: number;
  reporting_staff_ids: string[];
  reporting_officers: StaffSummary[];
  field_notes: string;
  incident_date: string | null;
  incident_time: string | null;
  facility: string | null;
  shift: string | null;
  location: string | null;
  category: string | null;
  classification: Record<string, unknown>;
  extracted_facts: Record<string, unknown>;
  gap_answers: Record<string, unknown>;
  charges: unknown[];
  validation: Record<string, unknown>;
  warnings: string[];
  created_at: string;
  updated_at: string;
}

export interface IncidentRevision {
  revision_id: string;
  revision_number: number;
  reason: string;
  changed_fields: string[];
  editor_staff_member_id: string;
  client_version: string | null;
  created_at: string;
  [key: string]: unknown;
}

export interface ReportSummary {
  report_id: string;
  incident_id: string;
  report_type: string;
  presentation: "document" | "copy_text";
  allowed_actions: string[];
  status: string;
  current_revision_number: number;
  reporting_officer: StaffSummary;
  preparer: StaffSummary;
  updated_at: string;
}

export interface ReportDetail extends ReportSummary {
  source_incident_revision_number: number | null;
  content: {
    narrative: string;
    editable_fields: Record<string, unknown>;
    validation: Record<string, unknown>;
    warnings: string[];
  };
  last_editor_staff_member_id: string;
  last_editor_display_name: string;
  created_at: string;
}

export interface ReportRevision {
  revision_id: string;
  revision_number: number;
  reason: string;
  changed_fields: string[];
  editor_staff_member_id: string;
  editor_display_name: string;
  source_incident_revision_number: number | null;
  client_version: string | null;
  created_at: string;
  is_current: boolean;
  content?: ReportDetail["content"];
}

export interface Completeness {
  state: "ready" | "needs_review" | "missing_information";
  missing_fields: string[];
  review_fields: string[];
}

export interface FormInstance {
  form_instance_id: string;
  source_incident_revision_number: number;
  populated_fields: Record<string, unknown>;
  manual_fields: Record<string, unknown>;
  completeness: Completeness;
  updated_at: string;
}

export interface PacketItem {
  packet_item_id: string;
  template_code: string;
  name: string;
  output_kind: "digital_document" | "physical_only";
  presentation: "document" | "physical";
  allowed_actions: string[];
  packet_group: "required" | "recommended" | "additional";
  packet_state: "selected" | "removed" | "not_applicable";
  selection_reason: string;
  not_applicable_reason: string | null;
  reporting_staff_member_id: string | null;
  source_incident_revision_number: number;
  definition: Record<string, unknown>;
  form_instance: FormInstance | null;
  physical_acknowledgment: {
    acknowledgment_id: string;
    acknowledged_by_staff_member_id: string;
    note: string | null;
    acknowledged_at: string;
  } | null;
}

export interface FormPreview {
  form_instance_id: string;
  packet_item_id: string;
  incident_id: string;
  template_code: string;
  template_name: string;
  render_kind: string;
  fields: Record<string, unknown>;
  completeness: Completeness;
}

export interface PhysicalGuidance {
  packet_item_id: string;
  incident_id: string;
  template_code: string;
  name: string;
  warning: string;
  description: string;
  obtain_from: string;
  guidance_fields: string[];
  guidance_values: Record<string, unknown>;
  source_incident_revision_number: number;
  acknowledgment: {
    acknowledgment_id: string;
    acknowledged_by_staff_member_id: string;
    note: string | null;
    acknowledged_at: string;
  } | null;
  allowed_actions: string[];
}

export interface JobView {
  job_id: string;
  incident_id: string;
  job_type: string;
  state: string;
  stage: string;
  base_incident_revision: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_code: string | null;
  result_reference: Record<string, unknown>;
}

export interface CreateIncidentInput {
  reporting_staff_ids: string[];
  incident_number?: string | null;
  incident_name?: string | null;
  incident_date?: string | null;
  incident_time?: string | null;
  facility?: string | null;
  shift?: string | null;
  location?: string | null;
  category?: string | null;
  field_notes: string;
  classification?: Record<string, unknown>;
  extracted_facts?: Record<string, unknown>;
  gap_answers?: Record<string, unknown>;
  charges?: unknown[];
  validation?: Record<string, unknown>;
  warnings?: string[];
}

function mutationKey(prefix: string): string {
  const id = typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}-${id}`;
}

function jsonHeaders(extra: Record<string, string> = {}): HeadersInit {
  return { "Content-Type": "application/json", ...extra };
}

export async function listIncidents(filters: {
  q?: string;
  relationship?: string;
  cursor?: string | null;
  limit?: number;
} = {}): Promise<IncidentPage> {
  const params = new URLSearchParams();
  if (filters.q?.trim()) params.set("q", filters.q.trim());
  params.set("relationship", filters.relationship ?? "all");
  params.set("limit", String(filters.limit ?? 25));
  if (filters.cursor) params.set("cursor", filters.cursor);
  return webApiRequest<IncidentPage>(`/incidents?${params.toString()}`);
}

export function getIncident(incidentId: string): Promise<IncidentRecord> {
  return webApiRequest(`/incidents/${incidentId}`);
}

export function createIncident(input: CreateIncidentInput): Promise<IncidentRecord> {
  return webApiRequest("/incidents", {
    method: "POST",
    headers: jsonHeaders({ "Idempotency-Key": mutationKey("incident-create") }),
    body: JSON.stringify(input),
  });
}

export function saveIncident(
  incident: IncidentRecord,
  changes: Partial<CreateIncidentInput>,
  reason: "autosave" | "manual_save" | "ai_result" = "manual_save",
): Promise<IncidentRecord> {
  const payload = {
    incident_number: incident.incident_number,
    incident_name: incident.incident_name,
    incident_date: incident.incident_date,
    incident_time: incident.incident_time,
    facility: incident.facility,
    shift: incident.shift,
    location: incident.location,
    category: incident.category,
    field_notes: incident.field_notes,
    classification: incident.classification,
    extracted_facts: incident.extracted_facts,
    gap_answers: incident.gap_answers,
    charges: incident.charges,
    validation: incident.validation,
    warnings: incident.warnings,
    ...changes,
    base_revision_number: incident.current_revision_number,
    reason,
  };
  return webApiRequest(`/incidents/${incident.incident_id}`, {
    method: "PATCH",
    headers: jsonHeaders({
      "Idempotency-Key": mutationKey("incident-save"),
      "If-Match": `"${incident.current_revision_number}"`,
    }),
    body: JSON.stringify(payload),
  });
}

export async function listIncidentRevisions(incidentId: string): Promise<IncidentRevision[]> {
  const page = await webApiRequest<{ items: IncidentRevision[] }>(
    `/incidents/${incidentId}/revisions?limit=100`,
  );
  return page.items;
}

export async function listReports(incidentId: string): Promise<ReportSummary[]> {
  const data = await webApiRequest<{ items: ReportSummary[] }>(
    `/incidents/${incidentId}/reports`,
  );
  return data.items;
}

export function getReport(reportId: string): Promise<ReportDetail> {
  return webApiRequest(`/reports/${reportId}`);
}

export function saveReport(report: ReportDetail, narrative: string): Promise<ReportDetail> {
  return webApiRequest(`/reports/${report.report_id}`, {
    method: "PATCH",
    headers: jsonHeaders({
      "Idempotency-Key": mutationKey("report-save"),
      "If-Match": `"${report.current_revision_number}"`,
    }),
    body: JSON.stringify({
      content: { ...report.content, narrative },
      base_revision_number: report.current_revision_number,
      reason: "manual_save",
    }),
  });
}

export async function listReportRevisions(reportId: string): Promise<ReportRevision[]> {
  const page = await webApiRequest<{ items: ReportRevision[] }>(
    `/reports/${reportId}/revisions?limit=100`,
  );
  return page.items;
}

export function submitJob(
  incidentId: string,
  jobType: "classify" | "extract" | "generate" | "disciplinary",
  revision: number,
): Promise<JobView> {
  return webApiRequest(`/incidents/${incidentId}/jobs/${jobType}`, {
    method: "POST",
    headers: jsonHeaders({ "Idempotency-Key": mutationKey(`job-${jobType}`) }),
    body: JSON.stringify({ base_revision_number: revision }),
  });
}

export function getJob(jobId: string): Promise<JobView> {
  return webApiRequest(`/jobs/${jobId}`);
}

export async function getPacket(incidentId: string): Promise<PacketItem[]> {
  const data = await webApiRequest<{ items: PacketItem[] }>(
    `/incidents/${incidentId}/packet`,
  );
  return data.items;
}

export async function rebuildPacket(
  incidentId: string,
  revision: number,
): Promise<PacketItem[]> {
  const data = await webApiRequest<{ items: PacketItem[] }>(
    `/incidents/${incidentId}/packet/rebuild`,
    {
      method: "POST",
      body: JSON.stringify({ incident_revision_number: revision }),
    },
  );
  return data.items;
}

export function populatePacketItem(
  packetItemId: string,
  revision: number,
): Promise<FormInstance> {
  return webApiRequest(`/packet-items/${packetItemId}/populate`, {
    method: "POST",
    body: JSON.stringify({ incident_revision_number: revision }),
  });
}

export function getFormPreview(formInstanceId: string): Promise<FormPreview> {
  return webApiRequest(`/form-instances/${formInstanceId}/preview`);
}

export function getPhysicalGuidance(packetItemId: string): Promise<PhysicalGuidance> {
  return webApiRequest(`/packet-items/${packetItemId}/physical`);
}

export function acknowledgePhysical(
  packetItemId: string,
  note: string,
): Promise<PhysicalGuidance["acknowledgment"]> {
  return webApiRequest(`/packet-items/${packetItemId}/physical/acknowledgment`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}

export function recordDocumentAction(input: {
  incident_id: string;
  incident_revision_number: number;
  action: string;
  packet_item_id?: string;
  report_id?: string;
}): Promise<{ event_id: string; action: string }> {
  return webApiRequest("/document-actions", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function downloadReportDocx(
  report: ReportSummary,
): Promise<void> {
  const csrf = readCookie("slut_web_csrf");
  const response = await fetch(
    `${WEB_API_BASE}/reports/${report.report_id}/export-docx?revision=${report.current_revision_number}`,
    {
      method: "POST",
      credentials: "include",
      headers: {
        "X-Client-Version": WEB_CLIENT_VERSION,
        "X-Request-ID": mutationKey("report-export-request"),
        "Idempotency-Key": mutationKey("report-export"),
        ...(csrf ? { "X-CSRF-Token": csrf } : {}),
      },
    },
  );
  if (!response.ok) throw new Error("Report download failed.");
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] ?? `${report.report_type}.docx`;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
