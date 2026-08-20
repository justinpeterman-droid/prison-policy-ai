import { z } from "zod";
export const SIGNOUT_UNITS = Array.from({ length: 9 }, (_, index) => `D${index + 1}`);
const staff = z.object({ staff_id: z.string().uuid(), display_name_snapshot: z.string().trim().min(1).max(160) }).strict();
export const signOutPayloadSchema = z.object({ schema_version: z.literal(1), work_date: z.iso.date(), shift: z.string().min(1).max(32), units: z.array(z.object({ unit_code: z.string(), staff: staff.nullable(), area_of_assignment: z.string().max(160) }).strict()).length(9), shift_supervisor: staff.nullable(), sign_out_date: z.string().nullable() }).strict();
export type SignOutPayload = z.infer<typeof signOutPayloadSchema>;
export function createEmptySignOutPayload(work_date: string, shift: string): SignOutPayload { return { schema_version: 1, work_date, shift, units: SIGNOUT_UNITS.map((unit_code) => ({ unit_code, staff: null, area_of_assignment: "" })), shift_supervisor: null, sign_out_date: null }; }
export function parseSignOutPayload(value: unknown): SignOutPayload { const parsed = signOutPayloadSchema.parse(value); if (parsed.units.some((unit, index) => unit.unit_code !== SIGNOUT_UNITS[index])) throw new Error("Detector units must preserve the approved D1-D9 order without duplicates."); return parsed; }
