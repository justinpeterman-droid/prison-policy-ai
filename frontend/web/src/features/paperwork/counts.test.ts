import { describe, expect, it } from "vitest";
import {
  calculateCountSheet,
  type CountSheetDefinition,
  validateCountValues,
} from "./counts";

const definition: CountSheetDefinition = {
  schemaVersion: 1,
  title: "Fictional NCU Days Count Training Sheet",
  rows: [
    { id: "housing_alpha", label: "Housing Alpha", section: "in_housing" },
    { id: "housing_bravo", label: "Housing Bravo", section: "in_housing" },
    { id: "infirmary", label: "Infirmary", section: "out_of_housing" },
  ],
  columns: [
    { id: "assigned", label: "Assigned" },
    { id: "present", label: "Present" },
    { id: "temporary", label: "Temporary" },
  ],
  operationalTotalColumn: "present",
};

describe("Count Sheet calculations", () => {
  it("returns signed reconciliation without changing officer entries", () => {
    const values = {
      housing_alpha: { assigned: 20, present: 18, temporary: 1 },
      housing_bravo: { assigned: 17, present: 17, temporary: 0 },
      infirmary: { assigned: 0, present: 2, temporary: 0 },
    };
    const original = structuredClone(values);

    const result = calculateCountSheet(definition, values, 38);

    expect(result.columnTotals).toEqual({ assigned: 37, present: 37, temporary: 1 });
    expect(result.operationalTotal).toBe(37);
    expect(result.reconciliationDifference).toBe(-1);
    expect(result.isReconciled).toBe(false);
    expect(values).toEqual(original);
  });

  it("treats omitted cells as zero while preserving sparse state", () => {
    const values = { housing_alpha: { present: 3 } };

    expect(validateCountValues(definition, values)).toEqual(values);
    expect(calculateCountSheet(definition, values, 3).columnTotals).toEqual({
      assigned: 0,
      present: 3,
      temporary: 0,
    });
    expect(values).toEqual({ housing_alpha: { present: 3 } });
  });

  it.each([
    { housing_alpha: { assigned: -1 } },
    { housing_alpha: { assigned: 1.5 } },
    { housing_alpha: { assigned: true } },
    { housing_alpha: { assigned: "1" } },
    { housing_alpha: { unknown: 1 } },
    { unknown: { assigned: 1 } },
  ])("rejects invalid values instead of coercing them", (values) => {
    expect(() => validateCountValues(definition, values)).toThrow();
  });
});
