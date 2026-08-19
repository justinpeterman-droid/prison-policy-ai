import type {
  CountSheetPayload,
  CountSheetStructure,
  CountSheetTotals,
  CountValue,
} from "./types";

function sameKeys(actual: Record<string, unknown>, expected: readonly string[]): boolean {
  const keys = Object.keys(actual);
  return keys.length === expected.length && expected.every((key) => key in actual);
}

function validCount(value: unknown): value is CountValue {
  return value === null || (
    typeof value === "number"
    && Number.isInteger(value)
    && Number.isSafeInteger(value)
    && value >= 0
  );
}

function count(value: CountValue): number {
  return value ?? 0;
}

export function validateCountPayload(
  structure: CountSheetStructure,
  payload: CountSheetPayload,
): CountSheetPayload {
  if (
    payload.schema_version !== 1
    || !sameKeys(payload.cells, structure.areas)
    || !sameKeys(payload.in_housing, structure.columns)
    || !sameKeys(payload.operational, structure.operational_fields)
  ) {
    throw new Error("Count Sheet values do not match the approved structure.");
  }
  for (const area of structure.areas) {
    const row = payload.cells[area];
    if (!row || !sameKeys(row, structure.columns)) {
      throw new Error("Count Sheet values do not match the approved structure.");
    }
    for (const column of structure.columns) {
      if (!validCount(row[column])) {
        throw new Error("Count Sheet values must be nonnegative whole numbers.");
      }
    }
  }
  for (const column of structure.columns) {
    if (!validCount(payload.in_housing[column])) {
      throw new Error("Count Sheet values must be nonnegative whole numbers.");
    }
  }
  for (const field of structure.operational_fields) {
    if (!validCount(payload.operational[field])) {
      throw new Error("Count Sheet values must be nonnegative whole numbers.");
    }
  }
  if (
    payload.count_started !== null
    && payload.count_ended !== null
    && payload.count_ended < payload.count_started
  ) {
    throw new Error("Count end cannot precede count start.");
  }
  return payload;
}

export function createBlankCountPayload(
  structure: CountSheetStructure,
): CountSheetPayload {
  return {
    schema_version: 1,
    count_started: null,
    count_ended: null,
    cells: Object.fromEntries(
      structure.areas.map((area) => [
        area,
        Object.fromEntries(structure.columns.map((column) => [column, null])),
      ]),
    ),
    in_housing: Object.fromEntries(
      structure.columns.map((column) => [column, null]),
    ),
    operational: Object.fromEntries(
      structure.operational_fields.map((field) => [field, null]),
    ),
  };
}

export function parseCountValue(value: string): CountValue {
  if (value === "") return null;
  if (!/^[0-9]+$/.test(value)) {
    throw new Error("Enter a nonnegative whole number.");
  }
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed)) {
    throw new Error("Enter a nonnegative whole number.");
  }
  return parsed;
}

export function calculateCountTotals(
  structure: CountSheetStructure,
  payload: CountSheetPayload,
): CountSheetTotals {
  validateCountPayload(structure, payload);
  const rowTotals: Record<string, number> = {};
  const outOfHousing: Record<string, number> = Object.fromEntries(
    structure.columns.map((column) => [column, 0]),
  );

  for (const area of structure.areas) {
    let rowTotal = 0;
    for (const column of structure.columns) {
      const value = count(payload.cells[area][column]);
      rowTotal += value;
      outOfHousing[column] += value;
    }
    rowTotals[area] = rowTotal;
  }

  const unitTotals = Object.fromEntries(
    structure.columns.map((column) => [
      column,
      outOfHousing[column] + count(payload.in_housing[column]),
    ]),
  );
  const housingTotal = Object.values(unitTotals).reduce(
    (total, value) => total + value,
    0,
  );
  const operationalTotal = structure.operational_fields.reduce(
    (total, field) => total + count(payload.operational[field]),
    0,
  );
  const difference = housingTotal - operationalTotal;

  return {
    row_totals: rowTotals,
    out_of_housing: outOfHousing,
    unit_totals: unitTotals,
    column_totals: { ...unitTotals },
    housing_total: housingTotal,
    operational_total: operationalTotal,
    difference,
    reconciled: difference === 0,
  };
}
