import { z } from "zod";
import { webApiRequest } from "../../../api/client";
import { mutationHeaders, runWithStepUp } from "../api";

const personSchema = z.object({
  staff_id: z.string(),
  display_name: z.string(),
}).passthrough();

const reportSchema = z.object({
  report_id: z.string(),
  report_type: z.string(),
  status: z.string(),
  current_revision_number: z.number().int().positive(),
  reporting_officer: personSchema,
  preparer: personSchema,
}).passthrough();

const detailSchema = z.object({
  incident_id: z.string(),
  incident_number: z.string().nullable(),
  incident_name: z.string().nullable(),
  records_status: z.string(),
  current_revision_number: z.number().int().positive(),
  reporting_officers: z.array(personSchema),
  preparers: z.array(personSchema),
  reports: z.array(reportSchema),
}).passthrough();

export interface AdminIncidentDetail {
  incidentId: string;
  incidentNumber: string | null;
  incidentName: string | null;
  recordsStatus: string;
  currentRevisionNumber: number;
  reportingOfficers: Array<{ staffId: string; displayName: string }>;
  preparers: Array<{ staffId: string; displayName: string }>;
  reports: Array<{
    reportId: string;
    reportType: string;
    status: string;
    currentRevisionNumber: number;
    reportingOfficer: { staffId: string; displayName: string };
    preparer: { staffId: string; displayName: string };
  }>;
}

function mapDetail(value: z.infer<typeof detailSchema>): AdminIncidentDetail {
  return {
    incidentId: value.incident_id,
    incidentNumber: value.incident_number,
    incidentName: value.incident_name,
    recordsStatus: value.records_status,
    currentRevisionNumber: value.current_revision_number,
    reportingOfficers: value.reporting_officers.map((person) => ({ staffId: person.staff_id, displayName: person.display_name })),
    preparers: value.preparers.map((person) => ({ staffId: person.staff_id, displayName: person.display_name })),
    reports: value.reports.map((report) => ({
      reportId: report.report_id,
      reportType: report.report_type,
      status: report.status,
      currentRevisionNumber: report.current_revision_number,
      reportingOfficer: { staffId: report.reporting_officer.staff_id, displayName: report.reporting_officer.display_name },
      preparer: { staffId: report.preparer.staff_id, displayName: report.preparer.display_name },
    })),
  };
}

export async function getAdminIncidentDetail(incidentId: string): Promise<AdminIncidentDetail> {
  return mapDetail(detailSchema.parse(await webApiRequest<unknown>(`/admin/incidents/${incidentId}`)));
}

export async function changeAdminRecordsStatus(
  incidentId: string,
  recordsStatus: "in_progress" | "completed" | "archived",
  baseRevisionNumber: number,
): Promise<AdminIncidentDetail> {
  return mapDetail(detailSchema.parse(await webApiRequest<unknown>(`/admin/incidents/${incidentId}/records-status`, {
    method: "PATCH",
    headers: mutationHeaders(),
    body: JSON.stringify({ records_status: recordsStatus, base_revision_number: baseRevisionNumber }),
  })));
}

export async function restoreAdminIncident(
  incidentId: string,
  revisionNumber: number,
  reason: string,
  pin: string,
): Promise<AdminIncidentDetail> {
  return runWithStepUp(pin, "report_restore", async () => mapDetail(detailSchema.parse(
    await webApiRequest<unknown>(`/admin/incidents/${incidentId}/restore`, {
      method: "POST",
      headers: mutationHeaders(),
      body: JSON.stringify({ revision_number: revisionNumber, reason }),
    }),
  )));
}

export async function transferAdminReport(
  reportId: string,
  newOwnerStaffId: string,
  newPreparerStaffId: string | null,
  reason: string,
  pin: string,
): Promise<void> {
  await runWithStepUp(pin, "report_transfer", () => webApiRequest<unknown>(`/admin/reports/${reportId}/transfer`, {
    method: "POST",
    headers: mutationHeaders(),
    body: JSON.stringify({
      new_owner_staff_id: newOwnerStaffId,
      new_preparer_staff_id: newPreparerStaffId,
      reason,
    }),
  }));
}
