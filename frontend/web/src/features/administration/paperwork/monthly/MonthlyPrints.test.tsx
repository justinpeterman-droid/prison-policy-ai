import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MONTHLY_PRINT_TEMPLATES } from "../../../../print/print-registry";
import { ChemicalAgentsPrint } from "./ChemicalAgentsPrint";
import { ContrabandSearchPrint } from "./ContrabandSearchPrint";
import { WindowsBarsDoorsPrint } from "./WindowsBarsDoorsPrint";

const prefill = { month: "2026-08", shift: "D", shiftSupervisor: "Sgt. Riley Jordan" };
const byCode = (code: (typeof MONTHLY_PRINT_TEMPLATES)[number]["code"]) => MONTHLY_PRINT_TEMPLATES.find((definition) => definition.code === code)!;

describe("monthly print documents", () => {
  it("renders all 31 blank Windows, Bars & Doors rows and the required note", () => {
    render(<WindowsBarsDoorsPrint definition={byCode("monthly_windows_bars_doors")} prefill={prefill} />);
    expect(screen.getByText("August 2026")).toBeInTheDocument();
    expect(screen.getByText("All bars will be checked with a rubber mallet.")).toBeInTheDocument();
    expect(within(screen.getByRole("table")).getAllByRole("row")).toHaveLength(32);
    expect(screen.getByLabelText("Comments area")).toBeEmptyDOMElement();
  });

  it("renders blank chemical-agent rows and required review areas", () => {
    render(<ChemicalAgentsPrint definition={byCode("monthly_chemical_agents")} prefill={prefill} />);
    expect(screen.getByText("COS Review / Date")).toBeInTheDocument();
    expect(screen.getByText("Warden Review / Date")).toBeInTheDocument();
    expect(screen.getByText("Sgt. Riley Jordan")).toBeInTheDocument();
  });

  it("keeps standard and expanded contraband schedules in their supplied order", () => {
    const { rerender } = render(<ContrabandSearchPrint definition={byCode("monthly_contraband_standard")} prefill={prefill} />);
    expect(screen.getAllByRole("row").slice(1).map((row) => row.textContent)).toEqual(expect.arrayContaining([expect.stringContaining("Gym"), expect.stringContaining("Laundry Press Area / Main Showers")]));
    rerender(<ContrabandSearchPrint definition={byCode("monthly_contraband_expanded")} prefill={prefill} />);
    expect(screen.getByText("Inside Maintenance")).toBeInTheDocument();
    expect(screen.getByLabelText("Additional Comments area")).toBeEmptyDOMElement();
  });
});
