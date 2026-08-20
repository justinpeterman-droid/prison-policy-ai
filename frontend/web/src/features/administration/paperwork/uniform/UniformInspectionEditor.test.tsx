import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DailyRecord } from "../api";
import * as paperworkApi from "../api";
import { parseUniformPayload, type UniformPayload } from "./model";
import { UniformInspectionEditor } from "./UniformInspectionEditor";


vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    fetchDailyPaperwork: vi.fn(),
    deriveUniformInspection: vi.fn(),
    saveDailyRecord: vi.fn(),
    recordDailyAction: vi.fn(),
  };
});


const AVERY = { staff_id: "00000000-0000-4000-8000-000000000401", display_name_snapshot: "Officer Avery Cole" };
const MORGAN = { staff_id: "00000000-0000-4000-8000-000000000402", display_name_snapshot: "Officer Morgan Lee" };

function payload(): UniformPayload {
  return {
    schema_version: 1,
    work_date: "2026-08-20",
    shift: "D",
    roster_record_id: "00000000-0000-4000-8000-000000000301",
    roster_revision_number: 2,
    inspector: null,
    rows: [
      { staff: AVERY, shirt: null, pants: "N/I", shoes: null, cap: null, coat: null, id: null, hair: null, nails: null, comments: "" },
      { staff: MORGAN, shirt: null, pants: null, shoes: null, cap: null, coat: null, id: null, hair: null, nails: null, comments: "" },
    ],
  };
}

function record(value = payload()): DailyRecord {
  return {
    recordId: "00000000-0000-4000-8000-000000000501",
    kind: "uniform_inspection",
    title: "Uniform Inspection Log",
    workDate: "2026-08-20",
    shift: "D",
    revision: 1,
    state: "saved",
    warningCount: 0,
    updatedAt: "2026-08-20T14:00:00Z",
    payload: value,
    validation: { unsatisfactory_count: 0, missing_comment_count: 0 },
    template: { schemaVersion: 1, title: "Uniform Inspection Log", printOrientation: "landscape", definition: {} },
  };
}

function renderEditor(current: DailyRecord | null, onRecordChange = vi.fn(), searchStaff = vi.fn().mockResolvedValue([])) {
  return render(<MemoryRouter><UniformInspectionEditor workDate="2026-08-20" shift="D" record={current} onRecordChange={onRecordChange} searchStaff={searchStaff} /></MemoryRouter>);
}

beforeEach(() => vi.clearAllMocks());

describe("Uniform Inspection editor", () => {
  it("shows source columns and bulk-marks blank values without overwriting exceptions", async () => {
    const user = userEvent.setup();
    renderEditor(record());

    const table = screen.getByRole("table", { name: "Uniform inspection matrix" });
    for (const heading of ["Name", "Shirt", "Pants", "Shoes", "Cap", "Coat", "I.D.", "Hair", "Nails", "Comments"]) {
      expect(within(table).getByRole("columnheader", { name: heading })).toBeInTheDocument();
    }
    await user.click(screen.getByRole("button", { name: "Mark Shirt Satisfactory" }));
    await user.click(screen.getByRole("button", { name: "Mark Pants Satisfactory" }));

    expect(screen.getByLabelText("Officer Avery Cole Shirt")).toHaveValue("S");
    expect(screen.getByLabelText("Officer Morgan Lee Shirt")).toHaveValue("S");
    expect(screen.getByLabelText("Officer Avery Cole Pants")).toHaveValue("N/I");
    expect(screen.getByLabelText("Officer Morgan Lee Pants")).toHaveValue("S");
  });

  it("blocks save on an uncommented U and preserves the editable exception", async () => {
    const user = userEvent.setup();
    const saved = record({ ...payload(), rows: payload().rows.map((row, index) => index ? row : { ...row, coat: "U", comments: "Coat missing required marking." }) });
    vi.mocked(paperworkApi.saveDailyRecord).mockResolvedValue(saved);
    const onRecordChange = vi.fn();
    renderEditor(record(), onRecordChange);

    await user.selectOptions(screen.getByLabelText("Officer Avery Cole Coat"), "U");
    await user.click(screen.getByRole("button", { name: "Save inspection" }));
    expect(screen.getByRole("alert")).toHaveTextContent(/Officer Avery Cole.*comment/i);
    expect(paperworkApi.saveDailyRecord).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Officer Avery Cole Coat")).toHaveValue("U");

    await user.type(screen.getByLabelText("Officer Avery Cole Comments"), "Coat missing required marking.");
    await user.click(screen.getByRole("button", { name: "Save inspection" }));
    await waitFor(() => expect(paperworkApi.saveDailyRecord).toHaveBeenCalled());
    expect(onRecordChange).toHaveBeenCalledWith(saved);
  });

  it("autosaves a change to an existing inspection after the operator pauses entry", async () => {
    const user = userEvent.setup();
    const saved = record({ ...payload(), inspector: AVERY });
    vi.mocked(paperworkApi.saveDailyRecord).mockResolvedValue(saved);
    renderEditor(record());

    await user.selectOptions(screen.getByLabelText("Officer Avery Cole Shirt"), "S");
    await waitFor(() => expect(paperworkApi.saveDailyRecord).toHaveBeenCalledWith(expect.objectContaining({
      reason: "autosave",
      recordId: "00000000-0000-4000-8000-000000000501",
    })), { timeout: 2_500 });
  });

  it("imports unique staff from the saved assignment roster", async () => {
    const user = userEvent.setup();
    const derived = record();
    vi.mocked(paperworkApi.fetchDailyPaperwork).mockResolvedValue({
      items: [{ recordId: "00000000-0000-4000-8000-000000000301", kind: "assignment_roster", title: "Shift Assignment Roster", workDate: "2026-08-20", shift: "D", revision: 2, state: "saved", warningCount: 0, updatedAt: "2026-08-20T13:00:00Z" }],
      nextCursor: null,
    });
    vi.mocked(paperworkApi.deriveUniformInspection).mockResolvedValue(derived);
    const onRecordChange = vi.fn();
    renderEditor(null, onRecordChange);

    await user.click(screen.getByRole("button", { name: "Import staff from Assignment Roster" }));

    await waitFor(() => expect(paperworkApi.deriveUniformInspection).toHaveBeenCalledWith(
      "00000000-0000-4000-8000-000000000301", "2026-08-20", "D",
    ));
    expect(onRecordChange).toHaveBeenCalledWith(derived);
    expect(within(screen.getByRole("table", { name: "Uniform inspection matrix" })).getByText("Officer Avery Cole")).toBeInTheDocument();
  });

  it("selects the inspecting staff member by searchable roster identity", async () => {
    const user = userEvent.setup();
    const searchStaff = vi.fn().mockResolvedValue([{
      staffId: "00000000-0000-4000-8000-000000000403",
      employeeNumber: "F1003",
      displayName: "Sgt. Riley Jordan",
      rank: "Sergeant",
      shift: "D",
      isActive: true,
      account: null,
    }]);
    renderEditor(record(), vi.fn(), searchStaff);

    const picker = screen.getByRole("combobox", { name: "Staff Conducting Inspection" });
    await user.type(picker, "Riley");
    await waitFor(() => expect(searchStaff).toHaveBeenLastCalledWith("Riley"));
    await user.keyboard("{ArrowDown}{Enter}");

    expect(picker).toHaveValue("Sgt. Riley Jordan");
    expect(screen.getByText(/2026-08-20.*D Shift/)).toBeInTheDocument();
  });

  it("rejects duplicate staff and renders the official print legend and distribution", () => {
    const duplicate = payload();
    duplicate.rows.push({ ...duplicate.rows[0] });
    expect(() => parseUniformPayload(duplicate)).toThrow(/unique|duplicate/i);

    renderEditor(record());
    const print = screen.getByTestId("uniform-inspection-print");
    expect(print).toHaveTextContent("Staff Conducting Inspection");
    expect(print).toHaveTextContent("S = Satisfactory");
    expect(print).toHaveTextContent("N/I = Needs Improvement");
    expect(print).toHaveTextContent("Distribution");
  });
});
