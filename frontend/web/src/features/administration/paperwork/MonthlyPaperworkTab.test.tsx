import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MonthlyPaperworkTab } from "./MonthlyPaperworkTab";
import * as paperworkApi from "./api";

vi.mock("./api", () => ({ fetchMonthlyPrintTemplates: vi.fn(), recordPrintTemplateAction: vi.fn() }));

const templates = [
  { code: "monthly_windows_bars_doors", title: "Windows, Bars & Doors Check Log", description: "Security checks", pageSize: "letter", orientation: "landscape", definition: { columns: ["Date", "Exterior Bks. Windows", "All Inmate Housing Windows", "Housing Doors", "All Cell Bars", "Officer's Signature"], footerNote: "All bars will be checked with a rubber mallet." } },
  { code: "monthly_chemical_agents", title: "Use of Chemical Agents Log", description: "Chemical agents", pageSize: "letter", orientation: "landscape", definition: { columns: ["Date", "Staff", "Inmate Name / #", "Conforms To Policy", "Medical Attention", "Supervisor"] } },
  { code: "monthly_contraband_standard", title: "Contraband Search Log — Standard Area Rotation", description: "Standard", pageSize: "letter", orientation: "landscape", definition: { columns: ["Date/Time", "Area Searched", "Contraband Found", "Searching Officers", "Disposition of Contraband"], schedule: ["Gym"] } },
  { code: "monthly_contraband_expanded", title: "Contraband Search Log — Expanded Area Rotation", description: "Expanded", pageSize: "letter", orientation: "landscape", definition: { columns: ["Date/Time", "Area Searched", "Contraband Found", "Searching Officers", "Disposition of Contraband"], schedule: ["Gym", "Inside Maintenance"] } },
] as const;

describe("MonthlyPaperworkTab", () => {
  it("offers exactly the supplied monthly forms and keeps selections while previewing", async () => {
    vi.mocked(paperworkApi.fetchMonthlyPrintTemplates).mockResolvedValue([...templates]);
    vi.mocked(paperworkApi.recordPrintTemplateAction).mockResolvedValue();
    render(<MonthlyPaperworkTab onPrint={vi.fn()} />);

    expect(await screen.findAllByTestId("monthly-template-card")).toHaveLength(4);
    expect(screen.getAllByText("Windows, Bars & Doors Check Log")).toHaveLength(2);
    expect(screen.getByText("Use of Chemical Agents Log")).toBeInTheDocument();
    expect(screen.getByText("Contraband Search Log — Standard Area Rotation")).toBeInTheDocument();
    expect(screen.getByText("Contraband Search Log — Expanded Area Rotation")).toBeInTheDocument();
    expect(screen.getByLabelText("Month")).toBeInTheDocument();
    expect(screen.getByLabelText("Shift")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("checkbox", { name: /windows, bars/i }));
    fireEvent.click(screen.getByRole("button", { name: /preview chemical/i }));

    expect(screen.getAllByRole("heading", { name: "Use of Chemical Agents Log" })).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Preview Monthly Packet (1)" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Clear selection" })).toBeEnabled();
  });
});
