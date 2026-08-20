import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DailyRecord } from "../api";
import * as paperworkApi from "../api";
import { createEmptyPerimeterPayload, type PerimeterDefinition } from "./model";
import { PerimeterCheckEditor } from "./PerimeterCheckEditor";


vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return { ...actual, fetchDailyTemplate: vi.fn(), saveDailyRecord: vi.fn(), createDailyRecord: vi.fn(), recordDailyAction: vi.fn() };
});

const definition: PerimeterDefinition = {
  values: ["S", "U"],
  value_labels: { S: "Satisfactory", U: "Unsatisfactory" },
  groups: [
    { code: "doors", label: "Doors", items: Array.from({ length: 25 }, (_, index) => ({ code: `doors_${String(index + 1).padStart(2, "0")}`, label: index === 0 ? "Isolation NW Corridor Exit" : index === 23 ? "Senstar Test" : index === 24 ? "Pipe Chases" : `Door Check ${index + 1}` })) },
    { code: "outside_doors", label: "Outside Doors", items: Array.from({ length: 19 }, (_, index) => ({ code: `outside_${String(index + 1).padStart(2, "0")}`, label: index === 17 ? "Manholes" : index === 18 ? "Metal Detector" : `Outside Door Check ${index + 1}` })) },
    { code: "fence_gates", label: "Fence & Gates", items: Array.from({ length: 21 }, (_, index) => ({ code: `fence_${String(index + 1).padStart(2, "0")}`, label: index === 20 ? "Fence And Alleyways" : `Fence Check ${index + 1}` })) },
  ],
  sign_off_fields: ["Perimeter Inspected by", "Signature", "Date / Time", "Senstar Inspected by", "Shift Supervisor's Signature", "Date / Time"],
};

function record(): DailyRecord {
  return { recordId: "00000000-0000-4000-8000-000000000701", kind: "perimeter_check", title: "Perimeter Check List", workDate: "2026-08-20", shift: "D", revision: 1, state: "saved", warningCount: 0, updatedAt: "2026-08-20T14:00:00Z", payload: createEmptyPerimeterPayload("2026-08-20", "D", definition), validation: { incomplete_count: 65, unsatisfactory_count: 0 }, template: { schemaVersion: 1, title: "Perimeter Check List", printOrientation: "portrait", definition: definition as unknown as Record<string, unknown> } };
}

beforeEach(() => vi.clearAllMocks());

describe("Perimeter Check editor", () => {
  it("renders every configured item once in source group order", () => {
    render(<MemoryRouter><PerimeterCheckEditor workDate="2026-08-20" shift="D" record={record()} onRecordChange={vi.fn()} searchStaff={vi.fn().mockResolvedValue([])} /></MemoryRouter>);
    expect(screen.getAllByRole("group", { name: /Doors|Fence & Gates/ })).toHaveLength(3);
    expect(screen.getAllByRole("combobox", { name: / perimeter result$/ })).toHaveLength(65);
    for (const label of ["Isolation NW Corridor Exit", "Senstar Test", "Pipe Chases", "Manholes", "Metal Detector", "Fence And Alleyways"]) {
      expect(screen.getByLabelText(`${label} perimeter result`)).toBeInTheDocument();
    }
  });

  it("bulk-marks only blank group items and keeps unsatisfactory exceptions", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><PerimeterCheckEditor workDate="2026-08-20" shift="D" record={record()} onRecordChange={vi.fn()} searchStaff={vi.fn().mockResolvedValue([])} /></MemoryRouter>);
    await user.selectOptions(screen.getByLabelText("Isolation NW Corridor Exit perimeter result"), "U");
    await user.click(screen.getByRole("button", { name: "Mark Doors Satisfactory" }));
    expect(screen.getByLabelText("Isolation NW Corridor Exit perimeter result")).toHaveValue("U");
    expect(screen.getByLabelText("Door Check 2 perimeter result")).toHaveValue("S");
    expect(screen.getByRole("status", { name: "Perimeter completion summary" })).toHaveTextContent("40 unchecked");
    expect(screen.getByRole("status", { name: "Perimeter completion summary" })).toHaveTextContent("1 unsatisfactory");
  });

  it("saves incomplete work and warns before previewing an incomplete print", async () => {
    const user = userEvent.setup();
    const saved = record();
    vi.mocked(paperworkApi.saveDailyRecord).mockResolvedValue(saved);
    const onRecordChange = vi.fn();
    render(<MemoryRouter><PerimeterCheckEditor workDate="2026-08-20" shift="D" record={record()} onRecordChange={onRecordChange} searchStaff={vi.fn().mockResolvedValue([])} /></MemoryRouter>);
    await user.click(screen.getByRole("button", { name: "Save perimeter check" }));
    await waitFor(() => expect(paperworkApi.saveDailyRecord).toHaveBeenCalled());
    expect(onRecordChange).toHaveBeenCalledWith(saved);

    await user.click(screen.getByRole("button", { name: "Preview" }));
    const dialog = screen.getByRole("dialog", { name: "Incomplete perimeter preview" });
    expect(dialog).toHaveTextContent(/65 unchecked/i);
    await user.click(within(dialog).getByRole("button", { name: "Continue to preview" }));
    expect(screen.getByRole("dialog", { name: "Perimeter Check print preview" })).toBeInTheDocument();
  });

  it("provides both sign-off lines and source-grouped portrait print content", () => {
    render(<MemoryRouter><PerimeterCheckEditor workDate="2026-08-20" shift="D" record={record()} onRecordChange={vi.fn()} searchStaff={vi.fn().mockResolvedValue([])} /></MemoryRouter>);
    expect(screen.getByRole("combobox", { name: "Perimeter Inspected by" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Senstar Inspected by" })).toBeInTheDocument();
    expect(screen.getByLabelText("Perimeter Signature")).toBeInTheDocument();
    expect(screen.getByLabelText("Shift Supervisor's Signature")).toBeInTheDocument();
    const print = screen.getByTestId("perimeter-check-print");
    expect(print).toHaveTextContent("Doors");
    expect(print).toHaveTextContent("Outside Doors");
    expect(print).toHaveTextContent("Fence & Gates");
    expect(print).toHaveTextContent("Satisfactory");
    expect(print).toHaveTextContent("Shift Supervisor's Signature");
  });
});
