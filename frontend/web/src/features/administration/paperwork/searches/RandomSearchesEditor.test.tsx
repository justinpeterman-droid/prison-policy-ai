import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DailyRecord } from "../api";
import * as paperworkApi from "../api";
import { createEmptyRandomSearchPayload } from "./model";
import { RandomSearchesEditor } from "./RandomSearchesEditor";

vi.mock("../api", async () => { const actual = await vi.importActual<typeof import("../api")>("../api"); return { ...actual, saveDailyRecord: vi.fn(), createDailyRecord: vi.fn(), recordDailyAction: vi.fn() }; });
function record(): DailyRecord { return { recordId: "00000000-0000-4000-8000-000000000801", kind: "random_search_log", title: "Random Searches Log", workDate: "2026-08-20", shift: "D", revision: 1, state: "saved", warningCount: 0, updatedAt: "2026-08-20T14:00:00Z", payload: createEmptyRandomSearchPayload("2026-08-20", "D"), validation: { incomplete_count: 16 }, template: { schemaVersion: 1, title: "Random Searches Log", printOrientation: "landscape", definition: {} } }; }
beforeEach(() => vi.clearAllMocks());

describe("Random Searches editor", () => {
  it("renders four source sections with four structured search blocks each", () => {
    render(<MemoryRouter><RandomSearchesEditor workDate="2026-08-20" shift="D" record={record()} onRecordChange={vi.fn()} searchStaff={vi.fn().mockResolvedValue([])} /></MemoryRouter>);
    for (const section of ["North 1", "North 2", "South 1", "South 2"]) expect(screen.getByRole("heading", { name: section })).toBeInTheDocument();
    expect(screen.getAllByTestId("random-search-block")).toHaveLength(16);
    const first = screen.getAllByTestId("random-search-block")[0];
    for (const label of ["Officer", "Date", "Time", "Individual Last Name", "Individual Number", "Barracks / Rack", "Contraband Found and Disposition"]) expect(within(first).getByLabelText(label)).toBeInTheDocument();
    expect(within(first).getByLabelText("Contraband Found and Disposition")).toHaveAttribute("maxlength", "2000");
  });

  it("preserves structured values and saves the edited log", async () => {
    const user = userEvent.setup(); const saved = record(); vi.mocked(paperworkApi.saveDailyRecord).mockResolvedValue(saved); const onRecordChange = vi.fn();
    render(<MemoryRouter><RandomSearchesEditor workDate="2026-08-20" shift="D" record={record()} onRecordChange={onRecordChange} searchStaff={vi.fn().mockResolvedValue([])} /></MemoryRouter>);
    const first = screen.getAllByTestId("random-search-block")[0];
    await user.type(within(first).getByLabelText("Individual Last Name"), "Fictional");
    await user.type(within(first).getByLabelText("Individual Number"), "I-100");
    await user.type(within(first).getByLabelText("Barracks / Rack"), "N1 / 04");
    await user.type(within(first).getByLabelText("Contraband Found and Disposition"), "No contraband located.");
    await user.click(screen.getByRole("button", { name: "Save random searches" }));
    await waitFor(() => expect(paperworkApi.saveDailyRecord).toHaveBeenCalled());
    const submitted = vi.mocked(paperworkApi.saveDailyRecord).mock.calls[0][0].payload as ReturnType<typeof createEmptyRandomSearchPayload>;
    expect(submitted.sections[0].blocks[0]).toMatchObject({ individual_last_name: "Fictional", individual_number: "I-100", barracks_rack: "N1 / 04" });
    expect(onRecordChange).toHaveBeenCalledWith(saved);
  });

  it("prints the four source sections as repeated officer blocks", () => {
    render(<MemoryRouter><RandomSearchesEditor workDate="2026-08-20" shift="D" record={record()} onRecordChange={vi.fn()} searchStaff={vi.fn().mockResolvedValue([])} /></MemoryRouter>);
    const print = screen.getByTestId("random-searches-print");
    expect(within(print).getAllByTestId("random-search-print-block")).toHaveLength(16);
    expect(print).toHaveTextContent("North 1"); expect(print).toHaveTextContent("South 2"); expect(print).toHaveTextContent("Contraband Found and Disposition");
  });
});
