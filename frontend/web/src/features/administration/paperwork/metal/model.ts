import { z } from "zod";


export const DETECTOR_CODES = Array.from({ length: 11 }, (_, index) => String(index + 1));
export const DETECTOR_POSITIONS = [
  "Inner left leg, pointing down",
  "Centered on front of body, pointing down",
  "Left side of body, pointing down",
  "Center of back, pointing down",
  "Center of back, pointing left",
  "Under left arm, pointing down",
  "Centered on top of head, pointing forward",
] as const;
export type DetectorResult = "P" | "F";

const staffSchema = z.object({ staff_id: z.string().uuid(), display_name_snapshot: z.string().trim().min(1).max(160) }).strict();
const positionSchema = z.object({ position_code: z.string(), result: z.enum(["P", "F"]).nullable() }).strict();
const detectorSchema = z.object({
  detector_code: z.string(),
  location: z.string().max(160),
  equipment_identifier: z.string().max(160),
  tests: z.array(positionSchema).length(7),
  corrective_action: z.string().max(2_000),
}).strict();
export const metalPayloadSchema = z.object({
  schema_version: z.literal(1),
  work_date: z.iso.date(),
  shift: z.string().min(1).max(32),
  detectors: z.array(detectorSchema).length(11),
  tested_by: staffSchema.nullable(),
  reviewed_by: staffSchema.nullable(),
  comments: z.string().max(10_000),
}).strict();
export type MetalPayload = z.infer<typeof metalPayloadSchema>;

export function createEmptyMetalPayload(workDate: string, shift: string): MetalPayload {
  return {
    schema_version: 1,
    work_date: workDate,
    shift,
    detectors: DETECTOR_CODES.map((detector_code) => ({
      detector_code,
      location: "",
      equipment_identifier: "",
      tests: DETECTOR_POSITIONS.map((_, index) => ({ position_code: `position_${index + 1}`, result: null })),
      corrective_action: "",
    })),
    tested_by: null,
    reviewed_by: null,
    comments: "",
  };
}

export function parseMetalPayload(value: unknown): MetalPayload {
  const parsed = metalPayloadSchema.parse(value);
  if (parsed.detectors.some((detector, index) => detector.detector_code !== DETECTOR_CODES[index])) throw new Error("Detectors do not match the approved order.");
  for (const detector of parsed.detectors) {
    if (detector.tests.some((test, index) => test.position_code !== `position_${index + 1}`)) throw new Error("Detector positions do not match the approved order.");
  }
  return parsed;
}

export function detectorMissingCorrectiveAction(payload: MetalPayload) {
  return payload.detectors.find((detector) => detector.tests.some((test) => test.result === "F") && !detector.corrective_action.trim()) ?? null;
}
