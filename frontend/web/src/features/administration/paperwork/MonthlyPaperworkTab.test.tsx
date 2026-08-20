import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MonthlyPaperworkTab } from "./MonthlyPaperworkTab";

describe("MonthlyPaperworkTab", () => {
  it("offers exactly the supplied monthly forms and keeps selections while previewing", () => {
    render(<MonthlyPaperworkTab onPrint={vi.fn()} />);

    expect(screen.getAllByTestId("monthly-template-card")).toHaveLength(4);
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
