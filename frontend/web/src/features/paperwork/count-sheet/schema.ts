import type { CountSheetStructure } from "./types";

const STRUCTURE_KEYS = new Set([
  "schema_version",
  "title",
  "columns",
  "areas",
  "operational_fields",
  "attachment_reminders",
]);

function stringList(value: unknown, name: string): string[] {
  if (
    !Array.isArray(value)
    || value.length === 0
    || !value.every((item) => typeof item === "string" && item.trim() === item && item.length > 0)
    || new Set(value).size !== value.length
  ) {
    throw new Error(`The Count Sheet ${name} structure is invalid.`);
  }
  return [...value];
}

export function parseCountSheetStructure(value: unknown): CountSheetStructure {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("The Count Sheet structure is invalid.");
  }
  const record = value as Record<string, unknown>;
  if (
    Object.keys(record).length !== STRUCTURE_KEYS.size
    || Object.keys(record).some((key) => !STRUCTURE_KEYS.has(key))
    || record.schema_version !== 1
    || typeof record.title !== "string"
    || !record.title.trim()
  ) {
    throw new Error("The Count Sheet structure is invalid.");
  }
  const columns = stringList(record.columns, "column");
  const areas = stringList(record.areas, "area");
  const operationalFields = stringList(
    record.operational_fields,
    "operational field",
  );
  const attachmentReminders = stringList(
    record.attachment_reminders,
    "attachment reminder",
  );
  if (!attachmentReminders.every((field) => operationalFields.includes(field))) {
    throw new Error("The Count Sheet attachment reminder structure is invalid.");
  }
  return {
    schema_version: 1,
    title: record.title,
    columns,
    areas,
    operational_fields: operationalFields,
    attachment_reminders: attachmentReminders,
  };
}
