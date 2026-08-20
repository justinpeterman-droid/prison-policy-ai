import { z } from "zod";


export const UNIFORM_COLUMNS = ["shirt", "pants", "shoes", "cap", "coat", "id", "hair", "nails"] as const;
export const UNIFORM_COLUMN_LABELS: Record<(typeof UNIFORM_COLUMNS)[number], string> = {
  shirt: "Shirt",
  pants: "Pants",
  shoes: "Shoes",
  cap: "Cap",
  coat: "Coat",
  id: "I.D.",
  hair: "Hair",
  nails: "Nails",
};
export const UNIFORM_VALUES = ["S", "N/I", "U", "NONE"] as const;
export type UniformValue = (typeof UNIFORM_VALUES)[number];

const staffSchema = z.object({
  staff_id: z.string().uuid(),
  display_name_snapshot: z.string().trim().min(1).max(160),
}).strict();
const valueSchema = z.enum(UNIFORM_VALUES).nullable();
const rowSchema = z.object({
  staff: staffSchema,
  shirt: valueSchema,
  pants: valueSchema,
  shoes: valueSchema,
  cap: valueSchema,
  coat: valueSchema,
  id: valueSchema,
  hair: valueSchema,
  nails: valueSchema,
  comments: z.string().max(500),
}).strict();

export const uniformPayloadSchema = z.object({
  schema_version: z.literal(1),
  work_date: z.iso.date(),
  shift: z.string().min(1).max(32),
  roster_record_id: z.string().uuid().nullable(),
  roster_revision_number: z.number().int().positive().nullable(),
  inspector: staffSchema.nullable(),
  rows: z.array(rowSchema).max(250),
}).strict();

export type UniformPayload = z.infer<typeof uniformPayloadSchema>;
export type UniformRow = UniformPayload["rows"][number];

export function createEmptyUniformPayload(workDate: string, shift: string): UniformPayload {
  return {
    schema_version: 1,
    work_date: workDate,
    shift,
    roster_record_id: null,
    roster_revision_number: null,
    inspector: null,
    rows: [],
  };
}

export function parseUniformPayload(value: unknown): UniformPayload {
  const parsed = uniformPayloadSchema.parse(value);
  const ids = parsed.rows.map((row) => row.staff.staff_id);
  if (new Set(ids).size !== ids.length) {
    throw new Error("Uniform inspection staff must be unique; duplicate staff are not allowed.");
  }
  if ((parsed.roster_record_id === null) !== (parsed.roster_revision_number === null)) {
    throw new Error("Roster provenance must include both record and revision.");
  }
  return parsed;
}

export function missingUniformComment(payload: UniformPayload): UniformRow | null {
  return payload.rows.find((row) => (
    UNIFORM_COLUMNS.some((column) => row[column] === "U") && !row.comments.trim()
  )) ?? null;
}
