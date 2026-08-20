import { z } from "zod";


export const dailyPaperworkKindSchema = z.enum([
  "assignment_roster",
  "uniform_inspection",
  "metal_detector_test",
  "perimeter_check",
  "random_search_log",
  "detector_sign_out",
]);

export const dailyRecordSummarySchema = z.object({
  record_id: z.string().uuid(),
  kind: dailyPaperworkKindSchema,
  title: z.string().min(1).max(200),
  work_date: z.iso.date(),
  shift: z.string().min(1).max(32),
  revision: z.number().int().positive(),
  current_revision_number: z.number().int().positive(),
  state: z.enum(["saved", "needs_attention"]),
  warning_count: z.number().int().nonnegative(),
  validation: z.record(z.string(), z.unknown()),
  created_by_staff_member_id: z.string().uuid(),
  last_editor_staff_member_id: z.string().uuid(),
  created_at: z.iso.datetime(),
  updated_at: z.iso.datetime(),
}).strict();

export const dailyRecordPageSchema = z.object({
  items: z.array(dailyRecordSummarySchema).max(50),
  next_cursor: z.null(),
}).strict();

export const templateSchema = z.object({
  schema_version: z.literal(1),
  title: z.string().min(1).max(200),
  print_orientation: z.enum(["portrait", "landscape"]),
  definition: z.record(z.string(), z.unknown()),
}).strict();

export const dailyTemplateResponseSchema = templateSchema.extend({
  kind: dailyPaperworkKindSchema,
}).strict();

const fullRecordBase = dailyRecordSummarySchema.extend({
  payload: z.record(z.string(), z.unknown()),
  template: templateSchema,
});

export const dailyRecordSchema = z.discriminatedUnion("kind", [
  fullRecordBase.extend({ kind: z.literal("assignment_roster") }).strict(),
  fullRecordBase.extend({ kind: z.literal("uniform_inspection") }).strict(),
  fullRecordBase.extend({ kind: z.literal("metal_detector_test") }).strict(),
  fullRecordBase.extend({ kind: z.literal("perimeter_check") }).strict(),
  fullRecordBase.extend({ kind: z.literal("random_search_log") }).strict(),
  fullRecordBase.extend({ kind: z.literal("detector_sign_out") }).strict(),
]);
