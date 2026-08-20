import { webApiRequest } from "../../../api/client";
import {
  dailyRecordPageSchema,
  dailyRecordSchema,
  dailyTemplateResponseSchema,
  dailyRevisionPageSchema,
  dailyPaperworkKindSchema,
} from "./schemas";
import { z } from "zod";
import type { MonthlyTemplateDefinition, PrintTemplateCode } from "../../../print/print-registry";


export type DailyPaperworkKind = z.infer<typeof dailyPaperworkKindSchema>;
export type DailyRecordState = "not_started" | "unsaved" | "saved" | "needs_attention";

export interface DailyRecordSummary {
  recordId: string;
  kind: DailyPaperworkKind;
  title: string;
  workDate: string;
  shift: string;
  revision: number;
  state: DailyRecordState;
  warningCount: number;
  updatedAt: string;
}

export interface DailyRecord extends DailyRecordSummary {
  payload: Record<string, unknown>;
  validation: Record<string, unknown>;
  template: {
    schemaVersion: 1;
    title: string;
    printOrientation: "portrait" | "landscape";
    definition: Record<string, unknown>;
  };
}

export interface DailyRecordPage {
  items: DailyRecordSummary[];
  nextCursor: null;
}

export interface DailyTemplate {
  kind: DailyPaperworkKind;
  schemaVersion: 1;
  title: string;
  printOrientation: "portrait" | "landscape";
  definition: Record<string, unknown>;
}

export interface DailyRevision {
  revisionNumber: number;
  reason: string;
  changedFields: string[];
  editorStaffMemberId: string;
  clientVersion: string | null;
  createdAt: string;
}

const printTemplateCodeSchema = z.enum([
  "monthly_windows_bars_doors",
  "monthly_chemical_agents",
  "monthly_contraband_standard",
  "monthly_contraband_expanded",
]);
const printTemplateSchema = z.object({
  code: printTemplateCodeSchema,
  title: z.string().min(1).max(200),
  period: z.literal("monthly"),
  category: z.string().min(1).max(80),
  schema_version: z.literal(1),
  page_size: z.literal("letter"),
  orientation: z.literal("landscape"),
  definition: z.object({
    columns: z.array(z.string().min(1)).min(1),
    schedule: z.array(z.string().min(1)).optional(),
    footer_note: z.string().min(1).optional(),
  }).passthrough(),
});

function printTemplate(value: z.infer<typeof printTemplateSchema>): MonthlyTemplateDefinition {
  return {
    code: value.code,
    title: value.title,
    description: value.category.replaceAll("_", " "),
    pageSize: value.page_size,
    orientation: value.orientation,
    definition: {
      columns: value.definition.columns,
      schedule: value.definition.schedule,
      footerNote: value.definition.footer_note,
    },
  };
}

export async function fetchMonthlyPrintTemplates(): Promise<MonthlyTemplateDefinition[]> {
  const parsed = z.object({ items: z.array(printTemplateSchema) }).parse(
    await webApiRequest<unknown>("/print-templates?period=monthly"),
  );
  return parsed.items.map(printTemplate);
}

export async function recordPrintTemplateAction(
  templateCodes: PrintTemplateCode[],
  action: "preview" | "print",
): Promise<void> {
  await webApiRequest<unknown>("/print-templates/actions", {
    method: "POST",
    body: JSON.stringify({ period: "monthly", template_codes: templateCodes, action }),
  });
}

function summary(value: z.infer<typeof dailyRecordPageSchema>["items"][number]): DailyRecordSummary {
  return {
    recordId: value.record_id,
    kind: value.kind,
    title: value.title,
    workDate: value.work_date,
    shift: value.shift,
    revision: value.revision,
    state: value.state,
    warningCount: value.warning_count,
    updatedAt: value.updated_at,
  };
}

function requestVersion(value: unknown): unknown {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;
  if (typeof record.template !== "object" || record.template === null || Array.isArray(record.template)) return null;
  return (record.template as Record<string, unknown>).schema_version;
}

export function parseDailyRecord(value: unknown): DailyRecord {
  if (requestVersion(value) !== 1) {
    throw new Error("This daily paperwork version is unsupported. Reload after the application is updated.");
  }
  const parsed = dailyRecordSchema.parse(value);
  return {
    ...summary(parsed),
    payload: parsed.payload,
    validation: parsed.validation,
    template: {
      schemaVersion: 1,
      title: parsed.template.title,
      printOrientation: parsed.template.print_orientation,
      definition: parsed.template.definition,
    },
  };
}

export async function fetchDailyPaperwork(
  workDate: string,
  shift: string,
): Promise<DailyRecordPage> {
  const params = new URLSearchParams({ work_date: workDate, shift });
  const parsed = dailyRecordPageSchema.parse(
    await webApiRequest<unknown>(`/admin/paperwork/daily?${params.toString()}`),
  );
  return { items: parsed.items.map(summary), nextCursor: null };
}

export async function fetchDailyRecord(
  kind: DailyPaperworkKind,
  recordId: string,
): Promise<DailyRecord> {
  return parseDailyRecord(
    await webApiRequest<unknown>(`/admin/paperwork/daily/${kind}/${recordId}`),
  );
}

export async function fetchDailyTemplate(kind: DailyPaperworkKind): Promise<DailyTemplate> {
  const parsed = dailyTemplateResponseSchema.parse(
    await webApiRequest<unknown>(`/admin/paperwork/daily/${kind}/template`),
  );
  if (parsed.kind !== kind) throw new Error("The daily paperwork template kind did not match the requested editor.");
  return {
    kind: parsed.kind,
    schemaVersion: parsed.schema_version,
    title: parsed.title,
    printOrientation: parsed.print_orientation,
    definition: parsed.definition,
  };
}

export async function fetchDailyRevisions(kind: DailyPaperworkKind, recordId: string): Promise<DailyRevision[]> {
  const parsed = dailyRevisionPageSchema.parse(await webApiRequest<unknown>(`/admin/paperwork/daily/${kind}/${recordId}/revisions`));
  return parsed.items.map((item) => ({ revisionNumber: item.revision_number, reason: item.reason, changedFields: item.changed_fields, editorStaffMemberId: item.editor_staff_member_id, clientVersion: item.client_version, createdAt: item.created_at }));
}

export async function restoreDailyRevision(kind: DailyPaperworkKind, recordId: string, revisionNumber: number): Promise<DailyRecord> {
  return parseDailyRecord(await webApiRequest<unknown>(`/admin/paperwork/daily/${kind}/${recordId}/restore`, { method: "POST", headers: { "Idempotency-Key": idempotencyKey() }, body: JSON.stringify({ revision_number: revisionNumber }) }));
}

function idempotencyKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `daily-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export async function createDailyRecord(input: {
  kind: DailyPaperworkKind;
  workDate: string;
  shift: string;
  payload: Record<string, unknown>;
}): Promise<DailyRecord> {
  return parseDailyRecord(await webApiRequest<unknown>(
    `/admin/paperwork/daily/${input.kind}`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey() },
      body: JSON.stringify({
        schema_version: 1,
        work_date: input.workDate,
        shift: input.shift,
        payload: input.payload,
        base_revision_number: null,
        reason: "manual_save",
      }),
    },
  ));
}

export async function copyPreviousDailyRecord(
  kind: DailyPaperworkKind,
  targetWorkDate: string,
  shift: string,
  sourceRecordId?: string,
): Promise<DailyRecord> {
  const body: Record<string, string> = {
    target_work_date: targetWorkDate,
    shift,
  };
  if (sourceRecordId) body.source_record_id = sourceRecordId;
  return parseDailyRecord(await webApiRequest<unknown>(
    `/admin/paperwork/daily/${kind}/copy-previous`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey() },
      body: JSON.stringify(body),
    },
  ));
}

export async function deriveUniformInspection(
  rosterRecordId: string,
  targetWorkDate: string,
  shift: string,
): Promise<DailyRecord> {
  return parseDailyRecord(await webApiRequest<unknown>(
    `/admin/paperwork/daily/assignment-roster/${rosterRecordId}/uniform-inspection`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey() },
      body: JSON.stringify({ target_work_date: targetWorkDate, shift }),
    },
  ));
}

export async function saveDailyRecord(input: {
  kind: DailyPaperworkKind;
  recordId: string;
  workDate: string;
  shift: string;
  revision: number;
  payload: Record<string, unknown>;
  reason: "autosave" | "manual_save" | "recovery";
}): Promise<DailyRecord> {
  return parseDailyRecord(await webApiRequest<unknown>(
    `/admin/paperwork/daily/${input.kind}/${input.recordId}`,
    {
      method: "PATCH",
      headers: {
        "Idempotency-Key": idempotencyKey(),
        "If-Match": `"${input.revision}"`,
      },
      body: JSON.stringify({
        schema_version: 1,
        work_date: input.workDate,
        shift: input.shift,
        payload: input.payload,
        base_revision_number: input.revision,
        reason: input.reason,
      }),
    },
  ));
}

export async function recordDailyAction(
  kind: DailyPaperworkKind,
  recordId: string,
  action: "preview" | "print" | "download_pdf",
): Promise<void> {
  await webApiRequest<unknown>(`/admin/paperwork/daily/${kind}/${recordId}/actions`, {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey() },
    body: JSON.stringify({ action }),
  });
}
