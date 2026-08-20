import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { DailyPaperworkTab } from "./DailyPaperworkTab";


describe("Daily Paperwork tab", () => {
  it("shows start actions for unsaved daily forms without inventing records", () => {
    render(
      <MemoryRouter>
        <DailyPaperworkTab workDate="2026-08-20" shift="D" records={[]} loading={false} error={null} />
      </MemoryRouter>,
    );

    const grid = screen.getByTestId("daily-record-grid");
    expect(within(grid).getByRole("link", { name: "Start Shift Assignment Roster" })).toBeInTheDocument();
    expect(within(grid).getAllByText("Not started")).toHaveLength(6);
    expect(screen.queryByText(/saved today/i)).not.toBeInTheDocument();
  });
});
