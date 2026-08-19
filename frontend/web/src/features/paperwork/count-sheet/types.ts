export type CountValue = number | null;

export interface CountSheetStructure {
  schema_version: 1;
  title: string;
  columns: string[];
  areas: string[];
  operational_fields: string[];
  attachment_reminders: string[];
}

export interface CountSheetPayload {
  schema_version: 1;
  count_started: string | null;
  count_ended: string | null;
  cells: Record<string, Record<string, CountValue>>;
  in_housing: Record<string, CountValue>;
  operational: Record<string, CountValue>;
}

export interface CountSheetTotals {
  row_totals: Record<string, number>;
  out_of_housing: Record<string, number>;
  unit_totals: Record<string, number>;
  column_totals: Record<string, number>;
  housing_total: number;
  operational_total: number;
  difference: number;
  reconciled: boolean;
}

export interface CountSheetRecord {
  record_id: string;
  kind: "count_sheet";
  work_date: string;
  shift: string | null;
  current_revision_number: number;
  payload: CountSheetPayload;
  validation: CountSheetTotals;
  created_by_staff_member_id: string;
  last_editor_staff_member_id: string;
  created_at: string;
  updated_at: string;
}

export interface CountSheetSummary {
  record_id: string;
  kind: "count_sheet";
  work_date: string;
  shift: string | null;
  current_revision_number: number;
  validation: Pick<
    CountSheetTotals,
    "housing_total" | "operational_total" | "difference" | "reconciled"
  >;
  created_by_staff_member_id: string;
  last_editor_staff_member_id: string;
  created_at: string;
  updated_at: string;
}

export interface CountSheetPageData {
  items: CountSheetSummary[];
  next_cursor: string | null;
}

export interface CountSheetRevision {
  revision_number: number;
  reason: string;
  changed_fields: string[];
  editor_staff_member_id: string;
  client_version: string;
  created_at: string;
}

export type CountSheetAction = "preview" | "print" | "download_pdf";
