import { webApiRequest } from "../../api/client";

export type FormOutputKind = "digital_document" | "physical_only";
export type FormCapability =
  | "preview"
  | "print"
  | "download_word"
  | "download_pdf"
  | "fillable"
  | "blank"
  | "attach_to_incident"
  | "physical_guidance";

export interface FormLibraryItem {
  templateId: string;
  code: string;
  name: string;
  category: string;
  purpose: string;
  whenUsed: string;
  outputKind: FormOutputKind;
  revisionLabel: string;
  capabilities: FormCapability[];
  frequent: boolean;
  obtainFrom: string | null;
}

export interface FormsLibraryFilters {
  q?: string;
  category?: string;
  limit?: number;
  cursor?: string;
}

export interface FormsLibraryResponse {
  items: FormLibraryItem[];
  categories: string[];
  nextCursor: string | null;
  requestPath: string;
}

export interface FormSelectionPlan {
  items: FormLibraryItem[];
  digitalItems: FormLibraryItem[];
  physicalItems: FormLibraryItem[];
}

export interface FormDownloadPlan {
  downloadableItems: FormLibraryItem[];
  skippedPhysicalItems: FormLibraryItem[];
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const CAPABILITIES = new Set<FormCapability>([
  "preview",
  "print",
  "download_word",
  "download_pdf",
  "fillable",
  "blank",
  "attach_to_incident",
  "physical_guidance",
]);
const ITEM_KEYS = [
  "template_id",
  "code",
  "name",
  "category",
  "purpose",
  "when_used",
  "output_kind",
  "revision_label",
  "capabilities",
  "frequent",
  "obtain_from",
] as const;

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
  if (keys.length !== wanted.length || keys.some((key, index) => key !== wanted[index])) {
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

function parseCapabilities(value: unknown): FormCapability[] {
  if (!Array.isArray(value) || value.length > CAPABILITIES.size) {
    throw new Error("Form capabilities are invalid.");
  }
  const result: FormCapability[] = [];
  for (const item of value) {
    if (typeof item !== "string" || !CAPABILITIES.has(item as FormCapability)) {
      throw new Error("Form capabilities are invalid.");
    }
    const capability = item as FormCapability;
    if (result.includes(capability)) throw new Error("Form capabilities are invalid.");
    result.push(capability);
  }
  return result;
}

function parseItem(
  value: unknown,
  options: { detail?: boolean } = {},
): FormLibraryItem {
  const row = object(value, "Forms Library item");
  const detail = options.detail ?? false;
  exactKeys(
    row,
    detail ? [...ITEM_KEYS, "definition"] : ITEM_KEYS,
    "Forms Library item",
  );
  if (detail) object(row.definition, "Form definition");

  const templateId = text(row.template_id, "Template ID", 36);
  if (!UUID.test(templateId)) throw new Error("Template ID is invalid.");
  const outputKind = row.output_kind;
  if (outputKind !== "digital_document" && outputKind !== "physical_only") {
    throw new Error("Form output kind is invalid.");
  }
  if (typeof row.frequent !== "boolean") throw new Error("Frequent-form marker is invalid.");
  const capabilities = parseCapabilities(row.capabilities);
  if (outputKind === "physical_only") {
    if (
      !capabilities.includes("physical_guidance")
      || capabilities.some((item) => ["preview", "print", "download_word", "download_pdf"].includes(item))
    ) {
      throw new Error("Physical form capabilities are invalid.");
    }
  }

  return {
    templateId,
    code: text(row.code, "Form code", 80),
    name: text(row.name, "Form name", 200),
    category: text(row.category, "Form category", 80),
    purpose: text(row.purpose, "Form purpose", 500),
    whenUsed: text(row.when_used, "Form use guidance", 500),
    outputKind,
    revisionLabel: text(row.revision_label, "Revision label", 120),
    capabilities,
    frequent: row.frequent,
    obtainFrom: nullableText(row.obtain_from, "Obtain-from guidance", 200),
  };
}

export function parseFormsLibraryItem(value: unknown): FormLibraryItem {
  return parseItem(value);
}

function parseCategories(value: unknown): string[] {
  if (!Array.isArray(value) || value.length > 100) {
    throw new Error("Forms Library categories are invalid.");
  }
  const categories = value.map((item) => text(item, "Form category", 80));
  if (new Set(categories).size !== categories.length) {
    throw new Error("Forms Library categories are invalid.");
  }
  return categories;
}

function parsePage(value: unknown): Omit<FormsLibraryResponse, "requestPath"> {
  const envelope = object(value, "Forms Library response");
  exactKeys(envelope, ["items", "categories", "next_cursor"], "Forms Library response");
  if (!Array.isArray(envelope.items)) throw new Error("Forms Library items are invalid.");
  const nextCursor = envelope.next_cursor;
  if (nextCursor !== null && typeof nextCursor !== "string") {
    throw new Error("Forms Library cursor is invalid.");
  }
  return {
    items: envelope.items.map(parseFormsLibraryItem),
    categories: parseCategories(envelope.categories),
    nextCursor,
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
  if (filters.limit !== undefined) {
    if (!Number.isInteger(filters.limit) || filters.limit < 1 || filters.limit > 50) {
      throw new Error("Page size is invalid.");
    }
    params.set("limit", String(filters.limit));
  }
  if (filters.cursor) params.set("cursor", filters.cursor);

  const path = `/forms${params.size ? `?${params.toString()}` : ""}`;
  const raw = await webApiRequest<unknown>(path);
  return { ...parsePage(raw), requestPath: path };
}

function selectionBody(templateIds: string[]): string {
  if (!Array.isArray(templateIds) || !templateIds.length || templateIds.length > 50) {
    throw new Error("Select between 1 and 50 forms.");
  }
  if (templateIds.some((item) => !UUID.test(item)) || new Set(templateIds).size !== templateIds.length) {
    throw new Error("The form selection is invalid.");
  }
  return JSON.stringify({ template_ids: templateIds });
}

function parseItemArray(value: unknown, label: string): FormLibraryItem[] {
  if (!Array.isArray(value)) throw new Error(`${label} is invalid.`);
  return value.map((item) => parseItem(item, { detail: true }));
}

export async function previewFormSelection(
  templateIds: string[],
): Promise<FormSelectionPlan> {
  const raw = await webApiRequest<unknown>("/forms/selection/preview", {
    method: "POST",
    body: selectionBody(templateIds),
  });
  const envelope = object(raw, "Form selection preview");
  exactKeys(envelope, ["items", "digital_items", "physical_items"], "Form selection preview");
  return {
    items: parseItemArray(envelope.items, "Selected forms"),
    digitalItems: parseItemArray(envelope.digital_items, "Selected digital forms"),
    physicalItems: parseItemArray(envelope.physical_items, "Selected physical forms"),
  };
}

export async function prepareFormDownload(
  templateIds: string[],
): Promise<FormDownloadPlan> {
  const raw = await webApiRequest<unknown>("/forms/selection/download", {
    method: "POST",
    body: selectionBody(templateIds),
  });
  const envelope = object(raw, "Form download plan");
  exactKeys(
    envelope,
    ["downloadable_items", "skipped_physical_items"],
    "Form download plan",
  );
  return {
    downloadableItems: parseItemArray(envelope.downloadable_items, "Downloadable forms"),
    skippedPhysicalItems: parseItemArray(
      envelope.skipped_physical_items,
      "Skipped physical forms",
    ),
  };
}
