import { webApiRequest } from "../../api/client";
import {
  validateCountValues,
  type CountSheetDefinition,
  type CountValues,
} from "./counts";

export interface CountSheetRecord {
  recordId: string;
  recordDate: string;
  shift: string;
  revision: number;
  definitionSha256: string;
  values: CountValues;
  expectedOperationalTotal: number;
  updatedAt: string;
}

interface RawDefinition {
  schema_version: unknown;
  title: unknown;
  definition_sha256: unknown;
  rows: unknown;
  columns: unknown;
  operational_total_column: unknown;
}

const SHA256 = /^[0-9a-f]{64}$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function object(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`${label} is invalid.`);
  }
  return value as Record<string, unknown>;
}

function text(value: unknown, label: string, maximum: number): string {
  if (typeof value !== "string" || !value.trim() || value.length > maximum) {
    throw new Error(`${label} is invalid.`);
  }
  return value;
}

function whole(value: unknown, label: string, minimum = 0): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < minimum || value > 99_999) {
    throw new Error(`${label} is invalid.`);
  }
  return value;
}

export function parseCountDefinition(raw: unknown): {
  definition: CountSheetDefinition;
  sha256: string;
} {
  const value = object(raw, "Count Sheet definition") as unknown as RawDefinition;
  const rows = Array.isArray(value.rows)
    ? value.rows.map((rawRow) => {
        const row = object(rawRow, "Count row");
        return {
          id: text(row.id, "Count row ID", 64),
          label: text(row.label, "Count row label", 120),
          section: text(row.section, "Count row section", 64),
        };
      })
    : null;
  const columns = Array.isArray(value.columns)
    ? value.columns.map((rawColumn) => {
        const column = object(rawColumn, "Count column");
        return {
          id: text(column.id, "Count column ID", 64),
          label: text(column.label, "Count column label", 120),
        };
      })
    : null;
  if (!rows || !columns || value.schema_version !== 1) {
    throw new Error("Count Sheet definition is invalid.");
  }
  const sha256 = text(value.definition_sha256, "Count definition fingerprint", 64);
  if (!SHA256.test(sha256)) throw new Error("Count definition fingerprint is invalid.");
  const definition: CountSheetDefinition = {
    schemaVersion: 1,
    title: text(value.title, "Count title", 200),
    rows,
    columns,
    operationalTotalColumn: text(
      value.operational_total_column,
      "Operational total column",
      64,
    ),
  };
  validateCountValues(definition, {});
  return { definition, sha256 };
}

function parseCountRecord(
  raw: unknown,
  definition: CountSheetDefinition,
  expectedDefinitionSha256: string,
): CountSheetRecord {
  const value = object(raw, "Count Sheet record");
  const recordId = text(value.record_id, "Count record ID", 36);
  if (!UUID.test(recordId)) throw new Error("Count record ID is invalid.");
  const content = object(value.content, "Count content");
  const fields = object(content.fields, "Count fields");
  const definitionSha256 = text(fields.definition_sha256, "Count definition fingerprint", 64);
  if (definitionSha256 !== expectedDefinitionSha256) {
    throw new Error("This saved Count Sheet uses a different approved template revision.");
  }
  return {
    recordId,
    recordDate: text(value.record_date, "Count date", 10),
    shift: text(value.shift, "Count shift", 32),
    revision: whole(value.current_revision_number, "Count revision", 1),
    definitionSha256,
    values: validateCountValues(definition, fields.values),
    expectedOperationalTotal: whole(
      fields.expected_operational_total,
      "Expected operational total",
    ),
    updatedAt: text(value.updated_at, "Count update time", 40),
  };
}

export async function fetchCountDefinition(): Promise<{
  definition: CountSheetDefinition;
  sha256: string;
}> {
  return parseCountDefinition(await webApiRequest<unknown>("/count-sheet/definition"));
}

export async function lookupCountSheet(
  recordDate: string,
  shift: string,
  definition: CountSheetDefinition,
  definitionSha256: string,
): Promise<CountSheetRecord | null> {
  const params = new URLSearchParams({ date: recordDate, shift });
  const raw = object(
    await webApiRequest<unknown>(`/count-sheet?${params.toString()}`),
    "Count lookup",
  );
  return raw.item === null
    ? null
    : parseCountRecord(raw.item, definition, definitionSha256);
}

function idempotencyKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `count-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export async function createCountSheet(options: {
  recordDate: string;
  shift: string;
  values: CountValues;
  expectedOperationalTotal: number;
  definition: CountSheetDefinition;
  definitionSha256: string;
}): Promise<CountSheetRecord> {
  const raw = await webApiRequest<unknown>("/count-sheet", {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey() },
    body: JSON.stringify({
      record_date: options.recordDate,
      shift: options.shift,
      values: validateCountValues(options.definition, options.values),
      expected_operational_total: whole(
        options.expectedOperationalTotal,
        "Expected operational total",
      ),
    }),
  });
  return parseCountRecord(raw, options.definition, options.definitionSha256);
}

export async function saveCountSheet(options: {
  recordId: string;
  revision: number;
  values: CountValues;
  expectedOperationalTotal: number;
  reason: "autosave" | "manual_save";
  definition: CountSheetDefinition;
  definitionSha256: string;
}): Promise<CountSheetRecord> {
  const raw = await webApiRequest<unknown>(`/count-sheet/${options.recordId}`, {
    method: "PATCH",
    headers: {
      "Idempotency-Key": idempotencyKey(),
      "If-Match": `"${options.revision}"`,
    },
    body: JSON.stringify({
      values: validateCountValues(options.definition, options.values),
      expected_operational_total: whole(
        options.expectedOperationalTotal,
        "Expected operational total",
      ),
      base_revision_number: whole(options.revision, "Count revision", 1),
      reason: options.reason,
    }),
  });
  return parseCountRecord(raw, options.definition, options.definitionSha256);
}
