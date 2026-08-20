import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PaperworkCenterPage } from "./PaperworkCenterPage";
import * as paperworkApi from "./api";


vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return { ...actual, fetchDailyPaperwork: vi.fn() };
});


const SAVED_ROSTER: paperworkApi.DailyRecordSummary = {
  recordId: "00000000-0000-4000-8000-000000000101",
  kind: "assignment_roster",
  title: "Shift Assignment Roster",
  workDate: "2026-08-20",
  shift: "D",
  revision: 2,
  state: "needs_attention",
  warningCount: 3,
  updatedAt: "2026-08-20T14:00:00Z",
};


function renderPage(entry = "/admin/paperwork?tab=daily&work_date=2026-08-20&shift=D") {
  vi.mocked(paperworkApi.fetchDailyPaperwork).mockResolvedValue({
    items: [SAVED_ROSTER],
    nextCursor: null,
  });
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <PaperworkCenterPage />
    </MemoryRouter>,
  );
}


afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});


describe("Administrator Paperwork Center", () => {
  it("loads the selected date and shift and renders daily forms in approved order", async () => {
    renderPage();

    expect(screen.getByRole("tab", { name: "Daily" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByLabelText("Work date")).toHaveValue("2026-08-20");
    expect(screen.getByLabelText("Shift")).toHaveValue("D");
    await waitFor(() => expect(paperworkApi.fetchDailyPaperwork).toHaveBeenCalledWith("2026-08-20", "D"));

    const cards = screen.getByTestId("daily-record-grid");
    expect(within(cards).getAllByRole("heading", { level: 2 }).map((heading) => heading.textContent)).toEqual([
      "Shift Assignment Roster",
      "Uniform Inspection",
      "NCU Days Count",
      "Walk-Through Metal Detector Testing",
      "Daily Perimeter Checklist",
      "Daily Random Searches",
      "Handheld Detector Sign-Out",
    ]);
    expect(within(cards).getByRole("link", { name: "Open Shift Assignment Roster" })).toBeInTheDocument();
    expect(within(cards).getByText("3 warnings")).toBeInTheDocument();
    expect(within(cards).getByRole("link", { name: "Open NCU Days Count" })).toHaveAttribute("href", "/count-sheet");
  });

  it("keeps period tabs keyboard operable and URL-selected", async () => {
    renderPage();
    const daily = screen.getByRole("tab", { name: "Daily" });

    fireEvent.keyDown(daily, { key: "ArrowRight" });

    expect(screen.getByRole("tab", { name: "Weekly" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "Weekly Paperwork Library" })).toBeInTheDocument();
  });

  it("reloads saved-record search when date or shift changes", async () => {
    renderPage();
    await waitFor(() => expect(paperworkApi.fetchDailyPaperwork).toHaveBeenCalledTimes(1));

    fireEvent.change(screen.getByLabelText("Work date"), { target: { value: "2026-08-21" } });
    fireEvent.change(screen.getByLabelText("Shift"), { target: { value: "N" } });

    await waitFor(() => expect(paperworkApi.fetchDailyPaperwork).toHaveBeenLastCalledWith("2026-08-21", "N"));
  });

  it("opens the fillable assignment roster workspace from a start URL", () => {
    renderPage("/admin/paperwork?tab=daily&work_date=2026-08-20&shift=D&kind=assignment_roster");

    expect(screen.getByRole("heading", { name: "Shift Assignment Roster", level: 1 })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: /^Zone [1-5]$/ })).toHaveLength(5);
    expect(screen.getByRole("button", { name: "Save roster" })).toBeEnabled();
  });
});
