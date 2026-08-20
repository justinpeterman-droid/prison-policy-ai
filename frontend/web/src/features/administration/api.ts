import { webApiRequest } from "../../api/client";
import {
  adminAuditPageSchema,
  adminElevationSchema,
  adminHealthSchema,
  adminIncidentPageSchema,
  adminOverviewSchema,
  adminStaffPageSchema,
  reviewLabHandoffSchema,
} from "./schemas";

export type AdminPurpose =
  | "staff_write"
  | "account_create"
  | "account_role_status"
  | "account_reset_pin"
  | "account_unlock"
  | "account_revoke_sessions"
  | "incident_restore"
  | "report_transfer"
  | "review_lab_handoff";

export interface AdminElevationState {
  elevated: boolean;
  elevationExpiresAt: string | null;
}

export interface AdminPaperworkState {
  status: string;
  recordId: string | null;
  updatedAt: string | null;
}

export interface AdminOverview {
  todaysPaperwork: {
    assignmentRoster: AdminPaperworkState;
    uniformInspection: AdminPaperworkState;
  };
  incidentsNeedingAttention: Array<{
    incidentId: string;
    incidentNumber: string | null;
    incidentName: string | null;
    progress: { code: string; label: string; blockingCount: number };
    reportCount: number;
    requiredPaperworkCount: number;
    updatedAt: string | null;
  }>;
  accountConditions: { locked: number; deactivated: number; temporaryPin: number };
  systemAvailability: Record<string, string>;
  recentAdministrativeActivity: Array<{
    eventId: string;
    action: string;
    targetType: string | null;
    targetId: string | null;
    result: string;
    occurredAt: string | null;
  }>;
}

export interface AdminIncidentSummary {
  incidentId: string;
  incidentNumber: string | null;
  incidentName: string | null;
  incidentDate: string | null;
  category: string | null;
  facility: string | null;
  location: string | null;
  shift: string | null;
  recordsStatus: string;
  reportingOfficers: Array<{ staffId: string; displayName: string }>;
  preparers: Array<{ staffId: string; displayName: string }>;
  progress: { code: string; label: string; blockingCount: number };
  officerReportCount: number;
  requiredPaperworkCount: number;
  updatedAt: string | null;
}

export interface AdminStaffMember {
  staffId: string;
  employeeNumber: string;
  displayName: string;
  rank: string | null;
  shift: string | null;
  isActive: boolean;
  account: null | {
    accountId: string;
    role: "user" | "admin";
    status: string;
    mustChangePin: boolean;
  };
}

export interface AdminAuditEvent {
  eventId: string;
  occurredAt: string;
  action: string;
  targetType: string | null;
  targetId: string | null;
  result: string;
  requestId: string;
  details: Record<string, unknown>;
}

function idempotencyKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `admin-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export async function getAdminElevation(): Promise<AdminElevationState> {
  const value = adminElevationSchema.parse(await webApiRequest<unknown>("/admin/elevation"));
  return { elevated: value.elevated, elevationExpiresAt: value.elevation_expires_at };
}

export async function enterAdminElevation(pin: string): Promise<AdminElevationState> {
  const value = adminElevationSchema.parse(await webApiRequest<unknown>("/admin/elevation", {
    method: "POST",
    body: JSON.stringify({ pin }),
  }));
  return { elevated: value.elevated, elevationExpiresAt: value.elevation_expires_at };
}

export async function requestAdminStepUp(pin: string, purpose: AdminPurpose): Promise<void> {
  await webApiRequest<unknown>("/admin/step-up", {
    method: "POST",
    body: JSON.stringify({ pin, purpose }),
  });
}

export async function getAdminOverview(): Promise<AdminOverview> {
  const value = adminOverviewSchema.parse(await webApiRequest<unknown>("/admin/overview"));
  const mapPaperwork = (item: { status: string; record_id: string | null; updated_at: string | null }) => ({
    status: item.status,
    recordId: item.record_id,
    updatedAt: item.updated_at,
  });
  return {
    todaysPaperwork: {
      assignmentRoster: mapPaperwork(value.todays_paperwork.assignment_roster),
      uniformInspection: mapPaperwork(value.todays_paperwork.uniform_inspection),
    },
    incidentsNeedingAttention: value.incidents_needing_attention.map((item) => ({
      incidentId: item.incident_id,
      incidentNumber: item.incident_number,
      incidentName: item.incident_name,
      progress: {
        code: item.progress.code,
        label: item.progress.label,
        blockingCount: item.progress.blocking_count,
      },
      reportCount: item.report_count,
      requiredPaperworkCount: item.required_paperwork_count,
      updatedAt: item.updated_at,
    })),
    accountConditions: {
      locked: value.account_conditions.locked,
      deactivated: value.account_conditions.deactivated,
      temporaryPin: value.account_conditions.temporary_pin,
    },
    systemAvailability: value.system_availability,
    recentAdministrativeActivity: value.recent_administrative_activity.map((item) => ({
      eventId: item.event_id,
      action: item.action,
      targetType: item.target_type,
      targetId: item.target_id,
      result: item.result,
      occurredAt: item.occurred_at,
    })),
  };
}

export async function listAdminIncidents(input: { q?: string; recordsStatus?: string; cursor?: string } = {}) {
  const params = new URLSearchParams();
  if (input.q?.trim()) params.set("q", input.q.trim());
  if (input.recordsStatus) params.set("records_status", input.recordsStatus);
  if (input.cursor) params.set("cursor", input.cursor);
  params.set("limit", "25");
  const value = adminIncidentPageSchema.parse(
    await webApiRequest<unknown>(`/admin/incidents?${params.toString()}`),
  );
  return {
    items: value.items.map((item): AdminIncidentSummary => ({
      incidentId: item.incident_id,
      incidentNumber: item.incident_number,
      incidentName: item.incident_name,
      incidentDate: item.incident_date,
      category: item.category,
      facility: item.facility,
      location: item.location,
      shift: item.shift,
      recordsStatus: item.records_status,
      reportingOfficers: item.reporting_officers.map((person) => ({ staffId: person.staff_id, displayName: person.display_name })),
      preparers: item.preparers.map((person) => ({ staffId: person.staff_id, displayName: person.display_name })),
      progress: { code: item.progress.code, label: item.progress.label, blockingCount: item.progress.blocking_count },
      officerReportCount: item.officer_report_count,
      requiredPaperworkCount: item.required_paperwork_count,
      updatedAt: item.updated_at,
    })),
    nextCursor: value.next_cursor,
  };
}

export async function listAdminStaff(query = "") {
  const params = new URLSearchParams({ limit: "50" });
  if (query.trim()) params.set("query", query.trim());
  const value = adminStaffPageSchema.parse(await webApiRequest<unknown>(`/admin/staff?${params.toString()}`));
  return {
    items: value.items.map((item): AdminStaffMember => ({
      staffId: item.staff_id,
      employeeNumber: item.employee_number,
      displayName: item.display_name,
      rank: item.rank,
      shift: item.shift,
      isActive: item.is_active,
      account: item.account ? {
        accountId: item.account.account_id,
        role: item.account.role,
        status: item.account.status,
        mustChangePin: item.account.must_change_pin,
      } : null,
    })),
    nextCursor: value.next_cursor,
  };
}

export async function listAdminAudit(filters: { actionFamily?: string; result?: string } = {}) {
  const params = new URLSearchParams({ limit: "50" });
  if (filters.actionFamily) params.set("action_family", filters.actionFamily);
  if (filters.result) params.set("result", filters.result);
  const value = adminAuditPageSchema.parse(await webApiRequest<unknown>(`/admin/audit?${params.toString()}`));
  return {
    items: value.items.map((item): AdminAuditEvent => ({
      eventId: item.event_id,
      occurredAt: item.occurred_at,
      action: item.action,
      targetType: item.target_type,
      targetId: item.target_id,
      result: item.result,
      requestId: item.request_id,
      details: item.details,
    })),
    nextCursor: value.next_cursor,
  };
}

export async function getAdminHealth() {
  const value = adminHealthSchema.parse(await webApiRequest<unknown>("/admin/health"));
  return {
    checkedAt: value.checked_at,
    components: value.components,
    build: value.build,
    notices: value.notices,
  };
}

export async function issueReviewLabHandoff(): Promise<{ url: string; expiresAt: string }> {
  const value = reviewLabHandoffSchema.parse(await webApiRequest<unknown>("/admin/review-lab-handoffs", {
    method: "POST",
  }));
  return { url: value.url, expiresAt: value.expires_at };
}

export async function runWithStepUp<T>(
  pin: string,
  purpose: AdminPurpose,
  action: () => Promise<T>,
): Promise<T> {
  await requestAdminStepUp(pin, purpose);
  return action();
}

export function mutationHeaders(): HeadersInit {
  return { "Idempotency-Key": idempotencyKey() };
}
