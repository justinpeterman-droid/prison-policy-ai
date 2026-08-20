import { z } from "zod";

export const statusSchema = z.enum(["Operational", "Degraded", "Unavailable"]);

export const adminElevationSchema = z.object({
  elevated: z.boolean(),
  elevation_expires_at: z.string().nullable(),
}).strict();

const paperworkStateSchema = z.object({
  status: z.enum(["not_started", "saved", "needs_attention"]).or(z.string()),
  record_id: z.string().nullable(),
  updated_at: z.string().nullable(),
}).strict();

const incidentProgressSchema = z.object({
  code: z.string(),
  label: z.string(),
  blocking_count: z.number().int().nonnegative(),
}).strict();

const adminIncidentSummarySchema = z.object({
  incident_id: z.string(),
  incident_number: z.string().nullable(),
  incident_name: z.string().nullable(),
  incident_date: z.string().nullable(),
  category: z.string().nullable(),
  facility: z.string().nullable(),
  location: z.string().nullable(),
  shift: z.string().nullable(),
  records_status: z.string(),
  reporting_officers: z.array(z.object({ staff_id: z.string(), display_name: z.string() }).strict()),
  preparers: z.array(z.object({ staff_id: z.string(), display_name: z.string() }).strict()),
  last_editor: z.object({ staff_id: z.string(), display_name: z.string() }).strict().nullable(),
  progress: incidentProgressSchema,
  officer_report_count: z.number().int().nonnegative(),
  required_paperwork_count: z.number().int().nonnegative(),
  created_at: z.string().nullable(),
  updated_at: z.string().nullable(),
}).strict();

export const adminOverviewSchema = z.object({
  todays_paperwork: z.object({
    assignment_roster: paperworkStateSchema,
    uniform_inspection: paperworkStateSchema,
  }).strict(),
  incidents_needing_attention: z.array(z.object({
    incident_id: z.string(),
    incident_number: z.string().nullable(),
    incident_name: z.string().nullable(),
    progress: incidentProgressSchema,
    report_count: z.number().int().nonnegative(),
    required_paperwork_count: z.number().int().nonnegative(),
    updated_at: z.string().nullable(),
  }).strict()),
  account_conditions: z.object({
    locked: z.number().int().nonnegative(),
    deactivated: z.number().int().nonnegative(),
    temporary_pin: z.number().int().nonnegative(),
  }).strict(),
  system_availability: z.record(z.string(), z.string()),
  recent_administrative_activity: z.array(z.object({
    event_id: z.string(),
    action: z.string(),
    target_type: z.string().nullable(),
    target_id: z.string().nullable(),
    result: z.string(),
    occurred_at: z.string().nullable(),
  }).strict()),
}).strict();

export const adminIncidentPageSchema = z.object({
  items: z.array(adminIncidentSummarySchema),
  next_cursor: z.string().nullable(),
}).strict();

const linkedAccountSchema = z.object({
  account_id: z.string(),
  staff_id: z.string(),
  employee_number: z.string(),
  display_name: z.string(),
  role: z.enum(["user", "admin"]),
  status: z.string(),
  must_change_pin: z.boolean(),
  created_at: z.string().nullable(),
  updated_at: z.string().nullable(),
}).strict();

export const adminStaffPageSchema = z.object({
  items: z.array(z.object({
    staff_id: z.string(),
    employee_number: z.string(),
    rank: z.string().nullable(),
    first_name: z.string(),
    last_name: z.string(),
    display_name: z.string(),
    shift: z.string().nullable(),
    is_active: z.boolean(),
    account: linkedAccountSchema.nullable(),
    created_at: z.string().nullable(),
    updated_at: z.string().nullable(),
  }).strict()),
  next_cursor: z.string().nullable(),
}).strict();

export const adminAuditPageSchema = z.object({
  items: z.array(z.object({
    event_id: z.string(),
    occurred_at: z.string(),
    actor_account_id: z.string().nullable(),
    actor_staff_member_id: z.string().nullable(),
    action: z.string(),
    target_type: z.string().nullable(),
    target_id: z.string().nullable(),
    result: z.string(),
    request_id: z.string(),
    client_version: z.string().nullable(),
    details: z.record(z.string(), z.unknown()),
  }).strict()),
  next_cursor: z.string().nullable(),
}).strict();

export const adminHealthSchema = z.object({
  checked_at: z.string(),
  components: z.record(z.string(), statusSchema),
  build: z.record(z.string(), z.string()),
  notices: z.array(z.object({
    component: z.string(),
    status: statusSchema,
    message: z.string(),
  }).strict()),
}).strict();

export const reviewLabHandoffSchema = z.object({
  url: z.string().startsWith("/access-handoff#"),
  expires_at: z.string(),
}).strict();
