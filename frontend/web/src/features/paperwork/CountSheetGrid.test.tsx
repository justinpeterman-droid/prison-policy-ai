import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CountSheetGrid } from "./CountSheetGrid";
import type { CountSheetDefinition, CountValues } from "./counts";

const definition: CountSheetDefinition = {
  schemaVersion: 1,
  title: "Fictional Count Sheet",
  rows: [
    { id: "alpha", label: "Housing Alpha", section: "in_housing" },
    { id: "infirmary", label: "Infirmary", section: "out_of_housing" },
  ],
  columns: [
    { id: "assigned", label: "Assigned" },
    { id: "present", label: "Present" },
  ],
  operationalTotalColumn: "present",
};

afterEach(cleanup);

describe("Count Sheet grid", () => {
  it("shows totals and an explicit signed mismatch without changing values", () => {
    const values: CountValues = {
      alpha: { assigned: 10, present: 9 },
      infirmary: { assigned: 0, present: 0 },
    };
    const onValuesChange = vi.fn();

    render(
      <CountSheetGrid
        definition={definition}
        values={values}
        expectedOperationalTotal={10}
        onValuesChange={onValuesChange}
        onExpectedOperationalTotalChange={vi.fn()}
        onSave={vi.fn()}
        saveState="saved"
      />,
    );

    expect(screen.getByText("Difference: -1")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("does not reconcile");
    expect(screen.getByText("Operational total: 9")).toBeInTheDocument();
    expect(onValuesChange).not.toHaveBeenCalled();
  });

  it("accepts only sparse whole-number entries and preserves other cells", () => {
    const onValuesChange = vi.fn();
    render(
      <CountSheetGrid
        definition={definition}
        values={{ alpha: { assigned: 10 } }}
        expectedOperationalTotal={10}
        onValuesChange={onValuesChange}
        onExpectedOperationalTotalChange={vi.fn()}
        onSave={vi.fn()}
        saveState="unsaved"
      />,
    );

    fireEvent.change(screen.getByRole("textbox", { name: "Housing Alpha Present" }), {
      target: { value: "9" },
    });
    expect(onValuesChange).toHaveBeenCalledWith({
      alpha: { assigned: 10, present: 9 },
    });

    fireEvent.change(screen.getByRole("textbox", { name: "Housing Alpha Assigned" }), {
      target: { value: "" },
    });
    expect(onValuesChange).toHaveBeenLastCalledWith({ alpha: {} });
  });

  it("supports arrow-key movement through the grid", () => {
    render(
      <CountSheetGrid
        definition={definition}
        values={{}}
        expectedOperationalTotal={0}
        onValuesChange={vi.fn()}
        onExpectedOperationalTotalChange={vi.fn()}
        onSave={vi.fn()}
        saveState="saved"
      />,
    );
    const first = screen.getByRole("textbox", { name: "Housing Alpha Assigned" });
    const second = screen.getByRole("textbox", { name: "Housing Alpha Present" });
    first.focus();
    fireEvent.keyDown(first, { key: "ArrowRight" });
    expect(second).toHaveFocus();
  });

  it("exposes clear save states", () => {
    const { rerender } = render(
      <CountSheetGrid
        definition={definition}
        values={{}}
        expectedOperationalTotal={0}
        onValuesChange={vi.fn()}
        onExpectedOperationalTotalChange={vi.fn()}
        onSave={vi.fn()}
        saveState="saving"
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Saving");

    rerender(
      <CountSheetGrid
        definition={definition}
        values={{}}
        expectedOperationalTotal={0}
        onValuesChange={vi.fn()}
        onExpectedOperationalTotalChange={vi.fn()}
        onSave={vi.fn()}
        saveState="failed"
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Save failed");
  });
});
