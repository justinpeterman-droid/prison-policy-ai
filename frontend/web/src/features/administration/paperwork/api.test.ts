import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchDailyPaperwork, parseDailyRecord } from "./api";


const request = vi.fn();

vi.mock("../../../api/client", () => ({
  webApiRequest: (path: string, init?: RequestInit) => request(path, init),
}));


function rawSummary() {
  return {
    record_id: "00000000-0000-4000-8000-000000000101",
    kind: "assignment_roster",
    title: "Shift Assignment Roster",
    work_date: "2026-08-20",
    shift: "D",
    revision: 2,
    current_revision_number: 2,
    state: "needs_attention",
    warning_count: 3,
    validation: { coverage_warnings: [] },
    created_by_staff_member_id: "00000000-0000-4000-8000-000000000001",
    last_editor_staff_member_id: "00000000-0000-4000-8000-000000000001",
    created_at: "2026-08-20T13:00:00Z",
    updated_at: "2026-08-20T14:00:00Z",
  };
}


beforeEach(() => request.mockReset());


describe("Daily Paperwork API", () => {
  it("builds encoded date and shift filters and parses strict summaries", async () => {
    request.mockResolvedValue({ items: [rawSummary()], next_cursor: null });

    const page = await fetchDailyPaperwork("2026-08-20", "D Shift");

    expect(request).toHaveBeenCalledWith(
      "/admin/paperwork/daily?work_date=2026-08-20&shift=D+Shift",
      undefined,
    );
    expect(page.items[0]).toMatchObject({
      kind: "assignment_roster",
      revision: 2,
      warningCount: 3,
    });
  });

  it("rejects unsupported full-record schema versions before editor state", () => {
    expect(() => parseDailyRecord({
      ...rawSummary(),
      payload: { schema_version: 2 },
      template: {
        schema_version: 2,
        title: "Shift Assignment Roster",
        print_orientation: "landscape",
        definition: {},
      },
    })).toThrow(/unsupported|version/i);
  });
});
