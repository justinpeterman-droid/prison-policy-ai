import { webApiRequest } from "../../../api/client";
import {
  dailyRecordPageSchema,
  dailyRecordSchema,
  dailyPaperworkKindSchema,
} from "./schemas";
import type { z } from "zod";


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
