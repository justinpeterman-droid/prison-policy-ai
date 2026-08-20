import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { DailyRecord } from "../api";
import * as paperworkApi from "../api";
import { DailyRevisionPanel } from "./DailyRevisionPanel";

vi.mock("../api", async () => { const actual = await vi.importActual<typeof import("../api")>("../api"); return { ...actual, fetchDailyRevisions: vi.fn(), restoreDailyRevision: vi.fn() }; });
const record = { recordId: "00000000-0000-4000-8000-000000001001", kind: "assignment_roster", title: "Shift Assignment Roster", workDate: "2026-08-20", shift: "D", revision: 3, state: "saved", warningCount: 0, updatedAt: "2026-08-20T14:00:00Z", payload: {}, validation: {}, template: { schemaVersion: 1, title: "Shift Assignment Roster", printOrientation: "landscape", definition: {} } } satisfies DailyRecord;
describe("daily revision panel", () => {
  it("loads attributed safe metadata and confirms restore before replacing editor state", async () => {
    const user = userEvent.setup(); vi.mocked(paperworkApi.fetchDailyRevisions).mockResolvedValue([{ revisionNumber: 3, reason: "manual_save", changedFields: ["briefing_minutes"], editorStaffMemberId: "00000000-0000-4000-8000-000000000001", clientVersion: "0.1.0", createdAt: "2026-08-20T14:00:00Z" }, { revisionNumber: 1, reason: "manual_save", changedFields: [], editorStaffMemberId: "00000000-0000-4000-8000-000000000002", clientVersion: "0.1.0", createdAt: "2026-08-20T12:00:00Z" }]); const restored = { ...record, revision: 4 }; vi.mocked(paperworkApi.restoreDailyRevision).mockResolvedValue(restored); const onRestored = vi.fn();
    render(<DailyRevisionPanel record={record} onRestored={onRestored} />);
    await user.click(screen.getByRole("button", { name: "Revision history" }));
    await waitFor(() => expect(paperworkApi.fetchDailyRevisions).toHaveBeenCalledWith("assignment_roster", record.recordId));
    expect(screen.getByRole("status")).toHaveTextContent("2 revisions loaded.");
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
    expect(screen.getByRole("status")).toHaveAttribute("aria-atomic", "true");
    expect(screen.getAllByText(/manual_save/)[0]).toHaveTextContent("briefing_minutes"); expect(screen.getByText(/00000000-0000-4000-8000-000000000001/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Restore revision 1" })); const dialog = screen.getByRole("dialog", { name: "Restore revision 1" }); expect(dialog).toHaveTextContent(/creates a new attributed revision/i); await user.click(within(dialog).getByRole("button", { name: "Confirm restore" }));
    await waitFor(() => expect(paperworkApi.restoreDailyRevision).toHaveBeenCalledWith("assignment_roster", record.recordId, 1)); expect(onRestored).toHaveBeenCalledWith(restored);
  });

  it("announces a revision-history failure through the shared destructive message contract", async () => {
    const user = userEvent.setup();
    vi.mocked(paperworkApi.fetchDailyRevisions).mockRejectedValue(new Error("Revision service is unavailable."));

    render(<DailyRevisionPanel record={record} onRestored={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Revision history" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Revision service is unavailable.");
    expect(alert).toHaveClass("gow-message--destructive");
    expect(alert).toHaveAttribute("aria-live", "assertive");
    expect(alert).toHaveAttribute("aria-atomic", "true");
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
  });
});
