import { apiRequest, downloadAuthorizedFile, requestId } from "../../api/client";
import type {
  JobSummary,
  Relationship,
  ReportDetail,
  ReportStatus,
  ReportSummary,
} from "../../types";

interface RawReportSummary {
  report_id: string;
  incident_id: string;
  report_type: string;
  relationship: Relationship;
  reporting_officer_display_name: string;
  preparer_display_name: string;
  category: string | null;
  incident_date: string | null;
  status: ReportStatus;
  updated_at: string;
  current_revision_number: number;
}

interface RawReportDetail extends RawReportSummary {
  content: {
    schema_version: 1;
    narrative: string;
    editable_fields: Record<string, string | number | boolean | null>;
    validation: Record<string, unknown>;
    warnings: string[];
  };
  last_editor_display_name: string;
  created_at: string;
}

interface RawJob {
  id: string;
  incident_id: string;
  job_type: JobSummary["jobType"];
  state: JobSummary["state"];
  stage: string;
  created_at: string;
  completed_at: string | null;
  error_code: string | null;
}

function mapSummary(raw: RawReportSummary): ReportSummary {
  return {
    reportId: raw.report_id,
    incidentId: raw.incident_id,
    reportType: raw.report_type,
    relationship: raw.relationship,
    reportingOfficerDisplayName: raw.reporting_officer_display_name,
    preparerDisplayName: raw.preparer_display_name,
    category: raw.category,
    incidentDate: raw.incident_date,
    status: raw.status,
    updatedAt: raw.updated_at,
    currentRevisionNumber: raw.current_revision_number,
  };
}

export async function listReports(
  relationship: Relationship,
  options: { status?: ReportStatus; category?: string; limit?: number } = {},
): Promise<ReportSummary[]> {
  const params = new URLSearchParams({
    relationship,
    limit: String(options.limit ?? 25),
  });
  if (options.status) params.set("status", options.status);
  if (options.category) params.set("category", options.category);
  const response = await apiRequest<{ items: RawReportSummary[]; next_cursor: string | null }>(
    `/web-api/reports?${params.toString()}`,
  );
  return response.items.map(mapSummary);
}

function mapDetail(raw: RawReportDetail): ReportDetail {
  return {
    ...mapSummary(raw),
    lastEditorDisplayName: raw.last_editor_display_name,
    createdAt: raw.created_at,
    content: {
      schemaVersion: raw.content.schema_version,
      narrative: raw.content.narrative,
      editableFields: raw.content.editable_fields,
      validation: raw.content.validation,
      warnings: raw.content.warnings,
    },
  };
}

export async function getReport(reportId: string): Promise<ReportDetail> {
  const raw = await apiRequest<RawReportDetail>(`/web-api/reports/${reportId}`);
  return mapDetail(raw);
}

export async function saveReport(
  report: ReportDetail,
  narrative: string,
): Promise<ReportDetail> {
  const raw = await apiRequest<RawReportDetail>(`/web-api/reports/${report.reportId}`, {
    method: "PATCH",
    headers: {
      "Idempotency-Key": requestId("save"),
      "If-Match": `\"${report.currentRevisionNumber}\"`,
    },
    body: JSON.stringify({
      content: {
        schema_version: 1,
        narrative,
        editable_fields: report.content.editableFields,
        validation: report.content.validation,
        warnings: report.content.warnings,
      },
      base_revision_number: report.currentRevisionNumber,
      reason: "manual_save",
    }),
  });
  return mapDetail(raw);
}

export async function submitJob(
  incidentId: string,
  type: JobSummary["jobType"],
  baseRevisionNumber: number,
): Promise<JobSummary> {
  const raw = await apiRequest<RawJob>(`/web-api/incidents/${incidentId}/jobs/${type}`, {
    method: "POST",
    headers: { "Idempotency-Key": requestId(`job_${type}`) },
    body: JSON.stringify({ base_revision_number: baseRevisionNumber }),
  });
  return {
    id: raw.id,
    incidentId: raw.incident_id,
    jobType: raw.job_type,
    state: raw.state,
    stage: raw.stage,
    createdAt: raw.created_at,
    completedAt: raw.completed_at,
    errorCode: raw.error_code,
  };
}

export async function exportReport(reportId: string, revision: number): Promise<void> {
  await downloadAuthorizedFile(
    `/web-api/reports/${reportId}/export-docx?revision=${revision}`,
    `report-${reportId.slice(-8)}-revision-${revision}.docx`,
    {
      method: "POST",
      headers: { "Idempotency-Key": requestId("export") },
    },
  );
}
