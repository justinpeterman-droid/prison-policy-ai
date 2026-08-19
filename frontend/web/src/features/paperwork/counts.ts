export interface CountRowDefinition {
  id: string;
  label: string;
  section: string;
}

export interface CountColumnDefinition {
  id: string;
  label: string;
}

export interface CountSheetDefinition {
  schemaVersion: 1;
  title: string;
  rows: CountRowDefinition[];
  columns: CountColumnDefinition[];
  operationalTotalColumn: string;
}

export type CountValues = Record<string, Record<string, number>>;

export interface CountSheetCalculation {
  rowTotals: Record<string, number>;
  columnTotals: Record<string, number>;
  sectionTotals: Record<string, number>;
  operationalTotal: number;
  expectedOperationalTotal: number;
  reconciliationDifference: number;
  isReconciled: boolean;
}

const IDENTIFIER = /^[a-z][a-z0-9_]{1,63}$/;
const MAX_CELL_VALUE = 99_999;

function assertDefinition(definition: CountSheetDefinition): void {
  if (
    definition.schemaVersion !== 1 ||
    typeof definition.title !== "string" ||
    definition.title.trim().length === 0 ||
    definition.rows.length === 0 ||
    definition.columns.length === 0
  ) {
    throw new Error("The Count Sheet definition is invalid.");
  }
  const rowIds = new Set<string>();
  for (const row of definition.rows) {
    if (
      !IDENTIFIER.test(row.id) ||
      !IDENTIFIER.test(row.section) ||
      !row.label.trim() ||
      rowIds.has(row.id)
    ) {
      throw new Error("The Count Sheet row definition is invalid.");
    }
    rowIds.add(row.id);
  }
  const columnIds = new Set<string>();
  for (const column of definition.columns) {
    if (!IDENTIFIER.test(column.id) || !column.label.trim() || columnIds.has(column.id)) {
      throw new Error("The Count Sheet column definition is invalid.");
    }
    columnIds.add(column.id);
  }
  if (!columnIds.has(definition.operationalTotalColumn)) {
    throw new Error("The operational total column is unavailable.");
  }
}

function wholeCount(value: unknown): number {
  if (
    typeof value !== "number" ||
    !Number.isInteger(value) ||
    value < 0 ||
    value > MAX_CELL_VALUE
  ) {
    throw new Error(`Counts must be whole numbers from 0 through ${MAX_CELL_VALUE}.`);
  }
  return value;
}

export function validateCountValues(
  definition: CountSheetDefinition,
  rawValues: unknown,
): CountValues {
  assertDefinition(definition);
  if (typeof rawValues !== "object" || rawValues === null || Array.isArray(rawValues)) {
    throw new Error("Count values must be a row object.");
  }
  const rowIds = new Set(definition.rows.map((row) => row.id));
  const columnIds = new Set(definition.columns.map((column) => column.id));
  const values = rawValues as Record<string, unknown>;
  const normalized: CountValues = {};

  for (const [rowId, rawColumns] of Object.entries(values)) {
    if (!rowIds.has(rowId)) throw new Error("Count values contain an unknown row.");
    if (typeof rawColumns !== "object" || rawColumns === null || Array.isArray(rawColumns)) {
      throw new Error("Count row values are invalid.");
    }
    const columns: Record<string, number> = {};
    for (const [columnId, rawValue] of Object.entries(rawColumns)) {
      if (!columnIds.has(columnId)) {
        throw new Error("Count values contain an unknown column.");
      }
      columns[columnId] = wholeCount(rawValue);
    }
    normalized[rowId] = columns;
  }
  return normalized;
}

export function calculateCountSheet(
  definition: CountSheetDefinition,
  rawValues: unknown,
  expectedOperationalTotal: number,
): CountSheetCalculation {
  const values = validateCountValues(definition, rawValues);
  const expected = wholeCount(expectedOperationalTotal);
  const columnIds = definition.columns.map((column) => column.id);
  const columnTotals = Object.fromEntries(columnIds.map((id) => [id, 0]));
  const rowTotals: Record<string, number> = {};
  const sectionTotals: Record<string, number> = {};

  for (const row of definition.rows) {
    const rowValues = values[row.id] ?? {};
    let rowTotal = 0;
    for (const columnId of columnIds) {
      const value = rowValues[columnId] ?? 0;
      rowTotal += value;
      columnTotals[columnId] += value;
    }
    rowTotals[row.id] = rowTotal;
    sectionTotals[row.section] = (sectionTotals[row.section] ?? 0) + rowTotal;
  }

  const operationalTotal = columnTotals[definition.operationalTotalColumn];
  const reconciliationDifference = operationalTotal - expected;
  return {
    rowTotals,
    columnTotals,
    sectionTotals,
    operationalTotal,
    expectedOperationalTotal: expected,
    reconciliationDifference,
    isReconciled: reconciliationDifference === 0,
  };
}
