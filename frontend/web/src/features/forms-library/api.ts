import { webApiRequest } from "../../api/client";

export type FormOutputKind = "digital_document" | "physical_only";

export interface FormLibraryActions {
  preview: boolean;
  print: boolean;
  downloadWord: boolean;
  downloadPdf: boolean;
  addToIncident: boolean;
  physicalGuidance: boolean;
}

export interface FormLibraryItem {
  templateId: string;
  code: string;
  name: string;
  category: string;
  outputKind: FormOutputKind;
  revisionLabel: string | null;
  description: string;
  obtainFrom: string | null;
  actions: FormLibraryActions;
}

export interface FormsLibraryFilters {
  q?: string;
  category?: string;
  outputKind?: FormOutputKind;
  limit?: number;
  cursor?: string;
}

export interface FormsLibraryResponse {
  items: FormLibraryItem[];
  nextCursor: string | null;
  requestPath: string;
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function object(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`${label} is invalid.`);
  }
  return value as Record<string, unknown>;
}

function exactKeys(
  value: Record<string, unknown>,
  expected: readonly string[],
  label: string,
): void {
  const keys = Object.keys(value).sort();
  const wanted = [...expected].sort();
  if (keys.length !== wanted.length || keys.some((key: string, index: number) => key !== wanted[index])) {
    throw new Error(`${label} has an unsupported field.`);
  }
}

function text(value: unknown, label: string, maximum = 500): string {
  if (typeof value !== "string") throw new Error(`${label} is invalid.`);
  const cleaned = value.trim();
  if (!cleaned || cleaned.length > maximum) throw new Error(`${label} is invalid.`);
  return cleaned;
}

function nullableText(value: unknown, label: string, maximum = 500): string | null {
  if (value === null) return null;
  return text(value, label, maximum);
}

function bool(value: unknown, label: string): boolean {
  if (typeof value !== "boolean") throw new Error(`${label} is invalid.`);
  return value;
}

export function parseFormsLibraryItem(value: unknown): FormLibraryItem {
  const row = object(value, "Forms Library item");
  exactKeys(row, [
    "template_id",
    "code",
    "name",
    "category",
    "output_kind",
    "revision_label",
    "description",
    "obtain_from",
    "actions",
  ], "Forms Library item");
  const templateId = text(row.template_id, "Template ID", 36);
  if (!UUID.test(templateId)) throw new Error("Template ID is invalid.");
  const outputKind = row.output_kind;
  if (outputKind !== "digital_document" && outputKind !== "physical_only") {
    throw new Error("Form output kind is invalid.");
  }
  const rawActions = object(row.actions, "Form actions");
  exactKeys(rawActions, [
    "preview",
    "print",
    "download_word",
    "download_pdf",
    "add_to_incident",
    "physical_guidance",
  ], "Form actions");

  return {
    templateId,
    code: text(row.code, "Form code", 80),
    name: text(row.name, "Form name", 200),
    category: text(row.category, "Form category", 80),
    outputKind,
    revisionLabel: nullableText(row.revision_label, "Revision label", 120),
    description: text(row.description, "Form description", 500),
    obtainFrom: nullableText(row.obtain_from, "Obtain-from guidance", 200),
    actions: {
      preview: bool(rawActions.preview, "Preview action"),
      print: bool(rawActions.print, "Print action"),
      downloadWord: bool(rawActions.download_word, "Word action"),
      downloadPdf: bool(rawActions.download_pdf, "PDF action"),
      addToIncident: bool(rawActions.add_to_incident, "Incident action"),
      physicalGuidance: bool(rawActions.physical_guidance, "Physical guidance action"),
    },
  };
}

export async function fetchFormsLibrary(
  filters: FormsLibraryFilters = {},
): Promise<FormsLibraryResponse> {
  const params = new URLSearchParams();
  const query = filters.q?.trim();
  const category = filters.category?.trim();
  if (query) {
    if (query.length > 200) throw new Error("Search is too long.");
    params.set("q", query);
  }
  if (category) {
    if (category.length > 80) throw new Error("Category is too long.");
    params.set("category", category);
  }
  if (filters.outputKind) params.set("output_kind", filters.outputKind);
  if (filters.limit !== undefined) {
    if (!Number.isInteger(filters.limit) || filters.limit < 1 || filters.limit > 50) {
      throw new Error("Page size is invalid.");
    }
    params.set("limit", String(filters.limit));
  }
  if (filters.cursor) params.set("cursor", filters.cursor);

  const path = `/forms-library${params.size ? `?${params.toString()}` : ""}`;
  const raw = await webApiRequest<unknown>(path);
  const envelope = object(raw, "Forms Library response");
  exactKeys(envelope, ["items", "next_cursor"], "Forms Library response");
  if (!Array.isArray(envelope.items)) throw new Error("Forms Library items are invalid.");
  const nextCursor = envelope.next_cursor;
  if (nextCursor !== null && typeof nextCursor !== "string") {
    throw new Error("Forms Library cursor is invalid.");
  }
  return {
    items: envelope.items.map(parseFormsLibraryItem),
    nextCursor,
    requestPath: path,
  };
}
