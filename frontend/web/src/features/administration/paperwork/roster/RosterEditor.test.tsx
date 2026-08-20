import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DailyRecord } from "../api";
import * as paperworkApi from "../api";
import { createEmptyRosterPayload, ROSTER_DEFINITION } from "./model";
import { RosterEditor } from "./RosterEditor";


vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    createDailyRecord: vi.fn(),
    copyPreviousDailyRecord: vi.fn(),
    saveDailyRecord: vi.fn(),
    recordDailyAction: vi.fn(),
  };
});


function record(payload = createEmptyRosterPayload("2026-08-20", "D")): DailyRecord {
  return {
    recordId: "00000000-0000-4000-8000-000000000301",
    kind: "assignment_roster",
    title: "Shift Assignment Roster",
    workDate: "2026-08-20",
    shift: "D",
    revision: 1,
    state: "needs_attention",
    warningCount: 20,
    updatedAt: "2026-08-20T14:00:00Z",
    payload,
    validation: { coverage_warnings: [] },
    template: {
      schemaVersion: 1,
      title: "Shift Assignment Roster",
      printOrientation: "landscape",
      definition: ROSTER_DEFINITION as unknown as Record<string, unknown>,
    },
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});


describe("Shift Assignment Roster editor", () => {
  it("renders five approved zones, editable assignment columns, and reorders only within a zone", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter>
      <RosterEditor
        workDate="2026-08-20"
        shift="D"
        record={record()}
        onRecordChange={vi.fn()}
        searchStaff={vi.fn().mockResolvedValue([])}
      />
    </MemoryRouter>);

    expect(screen.getAllByRole("heading", { name: /^Zone [1-5]$/ })).toHaveLength(5);
    const zoneOne = screen.getByTestId("roster-zone-zone_1");
    expect(within(zoneOne).getByText("Bks 8 Control Booth")).toBeInTheDocument();
    expect(within(zoneOne).getAllByText("P1").length).toBeGreaterThan(0);
    expect(within(zoneOne).getByRole("combobox", { name: "Bks 8 Control Booth initial officer" })).toBeInTheDocument();
    expect(within(zoneOne).getByRole("combobox", { name: "Bks 8 Control Booth rotation officer" })).toBeInTheDocument();

    await user.click(within(zoneOne).getByRole("button", { name: "Move Bks 8 Control Booth down" }));
    const labels = within(zoneOne).getAllByTestId("roster-post-label").map((item) => item.textContent);
    expect(labels.slice(0, 2)).toEqual(["Bks 9-10 Control Booth", "Bks 8 Control Booth"]);
    expect(screen.getByTestId("roster-zone-zone_2")).toHaveTextContent("Bks 1 Control Booth");

    const dragged = within(zoneOne).getByRole("button", { name: "Drag Bks 9-10 Control Booth" });
    const target = within(zoneOne).getByText("Bks 9-10 Desk").closest("tr");
    expect(target).not.toBeNull();
    fireEvent.dragStart(dragged);
    fireEvent.dragOver(target!);
    fireEvent.drop(target!);
    expect(within(zoneOne).getAllByTestId("roster-post-label").slice(0, 3).map((item) => item.textContent)).toEqual([
      "Bks 8 Control Booth",
      "Bks 9-10 Desk",
      "Bks 9-10 Control Booth",
    ]);
  });

  it("keeps operational fields editable, reports coverage, and saves without reassigning posts", async () => {
    const user = userEvent.setup();
    const sourcePayload = createEmptyRosterPayload("2026-08-20", "D");
    const source = record(sourcePayload);
    const saved = record({ ...sourcePayload, briefing_minutes: "Keep north gate clear." });
    vi.mocked(paperworkApi.saveDailyRecord).mockResolvedValue(saved);
    const onRecordChange = vi.fn();
    render(<MemoryRouter>
      <RosterEditor
        workDate="2026-08-20"
        shift="D"
        record={source}
        onRecordChange={onRecordChange}
        searchStaff={vi.fn().mockResolvedValue([])}
      />
    </MemoryRouter>);

    expect(screen.getByRole("status", { name: "Roster coverage" })).toHaveTextContent(/P1 posts need review/i);
    await user.type(screen.getByLabelText("Shift briefing minutes"), "Keep north gate clear.");
    await user.selectOptions(screen.getByLabelText("Digital Camera"), "yes");
    await user.click(screen.getByLabelText("Roll call completed"));
    await user.click(screen.getByRole("button", { name: "Add leave entry" }));
    expect(screen.getByLabelText("Leave time 1")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save roster" }));

    await waitFor(() => expect(paperworkApi.saveDailyRecord).toHaveBeenCalled());
    const call = vi.mocked(paperworkApi.saveDailyRecord).mock.calls[0][0];
    expect(call.payload.briefing_minutes).toBe("Keep north gate clear.");
    expect(call.payload.zones).toEqual(source.payload.zones);
    expect(onRecordChange).toHaveBeenCalledWith(saved);
  });

  it("preserves edits made during a pending save and uses the returned revision next", async () => {
    const user = userEvent.setup();
    const sourcePayload = createEmptyRosterPayload("2026-08-20", "D");
    const source = record(sourcePayload);
    const firstSaved = {
      ...record({ ...sourcePayload, briefing_minutes: "Initial edit" }),
      revision: 2,
    };
    let resolveFirst!: (value: DailyRecord) => void;
    vi.mocked(paperworkApi.saveDailyRecord).mockReturnValueOnce(new Promise((resolve) => {
      resolveFirst = resolve;
    }));
    const onRecordChange = vi.fn();
    render(<MemoryRouter>
      <RosterEditor
        workDate="2026-08-20"
        shift="D"
        record={source}
        onRecordChange={onRecordChange}
        searchStaff={vi.fn().mockResolvedValue([])}
      />
    </MemoryRouter>);

    const briefing = screen.getByLabelText("Shift briefing minutes");
    await user.type(briefing, "Initial edit");
    await user.click(screen.getByRole("button", { name: "Save roster" }));
    await waitFor(() => expect(paperworkApi.saveDailyRecord).toHaveBeenCalledTimes(1));
    await user.type(briefing, " plus newer work");

    await act(async () => resolveFirst(firstSaved));

    await waitFor(() => expect(onRecordChange).toHaveBeenCalledWith(firstSaved));
    expect(briefing).toHaveValue("Initial edit plus newer work");
    expect(screen.getByRole("status", { name: "Roster announcement" })).toHaveTextContent(
      "Newer edits remain unsaved",
    );
    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();

    const secondSaved = {
      ...firstSaved,
      revision: 3,
      payload: { ...sourcePayload, briefing_minutes: "Initial edit plus newer work" },
    };
    vi.mocked(paperworkApi.saveDailyRecord).mockResolvedValueOnce(secondSaved);
    await user.click(screen.getByRole("button", { name: "Save roster" }));

    await waitFor(() => expect(paperworkApi.saveDailyRecord).toHaveBeenCalledTimes(2));
    expect(vi.mocked(paperworkApi.saveDailyRecord).mock.calls[1][0]).toMatchObject({
      revision: 2,
      payload: { briefing_minutes: "Initial edit plus newer work" },
    });
    await waitFor(() => expect(screen.getByText("Saved")).toBeInTheDocument());
  });

  it("confirms copy previous, explains reset fields, and returns the new record", async () => {
    const user = userEvent.setup();
    const copied = record();
    vi.mocked(paperworkApi.copyPreviousDailyRecord).mockResolvedValue(copied);
    const onRecordChange = vi.fn();
    render(<MemoryRouter>
      <RosterEditor
        workDate="2026-08-20"
        shift="D"
        record={null}
        onRecordChange={onRecordChange}
        searchStaff={vi.fn().mockResolvedValue([])}
      />
    </MemoryRouter>);

    await user.click(screen.getByRole("button", { name: "Copy previous roster" }));
    const dialog = screen.getByRole("dialog", { name: "Copy previous roster" });
    expect(dialog).toHaveTextContent(/signatures, leave entries, briefing minutes, and completion checks are cleared/i);
    await user.click(within(dialog).getByRole("button", { name: "Create copied roster" }));

    await waitFor(() => expect(paperworkApi.copyPreviousDailyRecord).toHaveBeenCalledWith(
      "assignment_roster", "2026-08-20", "D",
    ));
    expect(onRecordChange).toHaveBeenCalledWith(copied);
    expect(screen.getByRole("status", { name: "Roster announcement" })).toHaveTextContent(/created/i);
  });

  it("renders an official print document with unit, columns, warnings, signatures, and distribution", () => {
    render(<MemoryRouter>
      <RosterEditor
        workDate="2026-08-20"
        shift="D"
        record={record()}
        onRecordChange={vi.fn()}
        searchStaff={vi.fn().mockResolvedValue([])}
      />
    </MemoryRouter>);

    const print = screen.getByTestId("assignment-roster-print");
    expect(print).toHaveTextContent("North Central Unit");
    expect(print).toHaveTextContent("Initial Officer");
    expect(print).toHaveTextContent("Rotation Officer");
    expect(print).toHaveTextContent("P1 posts must be staffed");
    expect(print).toHaveTextContent("Lieutenant Signature");
    expect(print).toHaveTextContent("Assistant Warden");
  });
});
