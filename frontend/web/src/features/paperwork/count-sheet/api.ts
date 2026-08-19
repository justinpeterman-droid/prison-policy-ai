import { webApiRequest } from "../../../api/client";
import { parseCountSheetStructure } from "./schema";
import type {
  CountSheetAction,
  CountSheetPageData,
  CountSheetPayload,
  CountSheetRecord,
  CountSheetRevision,
  CountSheetStructure,
} from "./types";

function mutationKey(prefix: string): string {
  const id = typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}-${id}`;
}

function jsonHeaders(extra: Record<string, string> = {}): HeadersInit {
  return { "Content-Type": "application/json", ...extra };
}

export async function getCountSheetStructure(): Promise<CountSheetStructure> {
  return parseCountSheetStructure(
    await webApiRequest<unknown>("/paperwork/count-sheets/structure"),
  );
}

export function listCountSheets(cursor?: string | null): Promise<CountSheetPageData> {
  const params = new URLSearchParams({ kind: "count_sheet", limit: "25" });
  if (cursor) params.set("cursor", cursor);
  return webApiRequest(`/paperwork?${params.toString()}`);
}

export function getCountSheet(recordId: string): Promise<CountSheetRecord> {
  return webApiRequest(`/paperwork/count-sheets/${recordId}`);
}

export function saveCountSheet(input: {
  record: CountSheetRecord | null;
  workDate: string;
  shift: string | null;
  payload: CountSheetPayload;
  reason: "autosave" | "manual_save" | "recovery";
}): Promise<CountSheetRecord> {
  const body = {
    schema_version: 1,
    work_date: input.workDate,
    shift: input.shift,
    payload: input.payload,
    base_revision_number: input.record?.current_revision_number ?? null,
    reason: input.reason,
  };
  if (!input.record) {
    return webApiRequest("/paperwork/count-sheets", {
      method: "POST",
      headers: jsonHeaders({
        "Idempotency-Key": mutationKey("count-sheet-create"),
      }),
      body: JSON.stringify(body),
    });
  }
  return webApiRequest(`/paperwork/count-sheets/${input.record.record_id}`, {
    method: "PATCH",
    headers: jsonHeaders({
      "Idempotency-Key": mutationKey("count-sheet-save"),
      "If-Match": `"${input.record.current_revision_number}"`,
    }),
    body: JSON.stringify(body),
  });
}

export async function listCountSheetRevisions(
  recordId: string,
): Promise<CountSheetRevision[]> {
  const page = await webApiRequest<{ items: CountSheetRevision[] }>(
    `/paperwork/count-sheets/${recordId}/revisions?limit=100`,
  );
  return page.items;
}

export function restoreCountSheet(
  recordId: string,
  revisionNumber: number,
): Promise<CountSheetRecord> {
  return webApiRequest(`/paperwork/count-sheets/${recordId}/restore`, {
    method: "POST",
    headers: jsonHeaders({
      "Idempotency-Key": mutationKey("count-sheet-restore"),
    }),
    body: JSON.stringify({ revision_number: revisionNumber }),
  });
}

export function recordCountSheetAction(
  recordId: string,
  action: CountSheetAction,
): Promise<{
  recorded: true;
  record_id: string;
  kind: "count_sheet";
  revision_number: number;
  action: CountSheetAction;
}> {
  return webApiRequest(`/paperwork/count-sheets/${recordId}/actions`, {
    method: "POST",
    headers: jsonHeaders({
      "Idempotency-Key": mutationKey(`count-sheet-${action}`),
    }),
    body: JSON.stringify({ action }),
  });
}
