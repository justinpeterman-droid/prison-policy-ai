import { z } from "zod";


export interface PerimeterDefinition {
  values: ["S", "U"];
  value_labels: { S: string; U: string };
  groups: Array<{ code: string; label: string; items: Array<{ code: string; label: string }> }>;
  sign_off_fields: string[];
}
export type PerimeterResult = "S" | "U";

const definitionSchema = z.object({
  values: z.tuple([z.literal("S"), z.literal("U")]),
  value_labels: z.object({ S: z.string(), U: z.string() }).strict(),
  groups: z.array(z.object({ code: z.string(), label: z.string(), items: z.array(z.object({ code: z.string(), label: z.string() }).strict()) }).strict()).length(3),
  sign_off_fields: z.array(z.string()),
}).strict();
const staffSchema = z.object({ staff_id: z.string().uuid(), display_name_snapshot: z.string().trim().min(1).max(160) }).strict();
export const perimeterPayloadSchema = z.object({
  schema_version: z.literal(1),
  work_date: z.iso.date(),
  shift: z.string().min(1).max(32),
  checks: z.array(z.object({ check_code: z.string(), result: z.enum(["S", "U"]).nullable() }).strict()).length(65),
  perimeter_inspector: staffSchema.nullable(),
  perimeter_signature_name: z.string().max(160).nullable(),
  perimeter_inspected_at: z.string().nullable(),
  senstar_inspector: staffSchema.nullable(),
  supervisor_signature_name: z.string().max(160).nullable(),
  supervisor_signed_at: z.string().nullable(),
}).strict();
export type PerimeterPayload = z.infer<typeof perimeterPayloadSchema>;

export function parsePerimeterDefinition(value: unknown): PerimeterDefinition {
  const parsed = definitionSchema.parse(value);
  if (parsed.groups.flatMap((group) => group.items).length !== 65) throw new Error("The perimeter definition must contain 65 approved checks.");
  return parsed;
}

export function createEmptyPerimeterPayload(workDate: string, shift: string, definition: PerimeterDefinition): PerimeterPayload {
  return {
    schema_version: 1,
    work_date: workDate,
    shift,
    checks: definition.groups.flatMap((group) => group.items.map((item) => ({ check_code: item.code, result: null }))),
    perimeter_inspector: null,
    perimeter_signature_name: null,
    perimeter_inspected_at: null,
    senstar_inspector: null,
    supervisor_signature_name: null,
    supervisor_signed_at: null,
  };
}

export function parsePerimeterPayload(value: unknown, definition: PerimeterDefinition): PerimeterPayload {
  const parsed = perimeterPayloadSchema.parse(value);
  const approved = definition.groups.flatMap((group) => group.items.map((item) => item.code));
  if (parsed.checks.some((check, index) => check.check_code !== approved[index])) throw new Error("Perimeter checks do not match the approved source order.");
  return parsed;
}
