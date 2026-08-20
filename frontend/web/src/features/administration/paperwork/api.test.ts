import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  copyPreviousDailyRecord,
  createDailyRecord,
  deriveUniformInspection,
  fetchDailyPaperwork,
  fetchDailyTemplate,
  fetchDailyRevisions,
  parseDailyRecord,
  restoreDailyRevision,
} from "./api";


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

  it("creates a revision-one daily record with the visible date, shift, and payload", async () => {
    request.mockResolvedValue({
      ...rawSummary(),
      revision: 1,
      current_revision_number: 1,
      payload: { schema_version: 1 },
      template: {
        schema_version: 1,
        title: "Shift Assignment Roster",
        print_orientation: "landscape",
        definition: {},
      },
    });

    await createDailyRecord({
      kind: "assignment_roster",
      workDate: "2026-08-20",
      shift: "D",
      payload: { schema_version: 1 },
    });

    expect(request).toHaveBeenCalledWith(
      "/admin/paperwork/daily/assignment_roster",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "Idempotency-Key": expect.any(String) }),
        body: JSON.stringify({
          schema_version: 1,
          work_date: "2026-08-20",
          shift: "D",
          payload: { schema_version: 1 },
          base_revision_number: null,
          reason: "manual_save",
        }),
      }),
    );
  });

  it("copies the previous roster into the selected target date and shift", async () => {
    request.mockResolvedValue({
      ...rawSummary(),
      payload: { schema_version: 1 },
      template: {
        schema_version: 1,
        title: "Shift Assignment Roster",
        print_orientation: "landscape",
        definition: {},
      },
    });

    await copyPreviousDailyRecord("assignment_roster", "2026-08-21", "N");

    expect(request).toHaveBeenCalledWith(
      "/admin/paperwork/daily/assignment_roster/copy-previous",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ target_work_date: "2026-08-21", shift: "N" }),
      }),
    );
  });

  it("derives a uniform inspection from a saved roster revision", async () => {
    request.mockResolvedValue({
      ...rawSummary(),
      kind: "uniform_inspection",
      title: "Uniform Inspection Log",
      payload: { schema_version: 1 },
      template: {
        schema_version: 1,
        title: "Uniform Inspection Log",
        print_orientation: "landscape",
        definition: {},
      },
    });

    await deriveUniformInspection(
      "00000000-0000-4000-8000-000000000101",
      "2026-08-20",
      "D",
    );

    expect(request).toHaveBeenCalledWith(
      "/admin/paperwork/daily/assignment-roster/00000000-0000-4000-8000-000000000101/uniform-inspection",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ target_work_date: "2026-08-20", shift: "D" }),
      }),
    );
  });

  it("loads the sanitized template for an unstarted daily editor", async () => {
    request.mockResolvedValue({ kind: "perimeter_check", schema_version: 1, title: "Perimeter Check List", print_orientation: "portrait", definition: { groups: [] } });

    const template = await fetchDailyTemplate("perimeter_check");

    expect(request).toHaveBeenCalledWith("/admin/paperwork/daily/perimeter_check/template", undefined);
    expect(template).toMatchObject({ kind: "perimeter_check", schemaVersion: 1, printOrientation: "portrait" });
  });

  it("loads safe revision metadata and restores a selected revision", async () => {
    request.mockResolvedValueOnce({ items: [{ revision_number: 2, reason: "manual_save", changed_fields: ["briefing_minutes"], editor_staff_member_id: "00000000-0000-4000-8000-000000000001", client_version: "0.1.0", created_at: "2026-08-20T14:00:00Z" }], next_cursor: null });
    const revisions = await fetchDailyRevisions("assignment_roster", "00000000-0000-4000-8000-000000000101");
    expect(revisions[0]).toMatchObject({ revisionNumber: 2, changedFields: ["briefing_minutes"] });

    request.mockResolvedValueOnce({ ...rawSummary(), payload: { schema_version: 1 }, template: { schema_version: 1, title: "Shift Assignment Roster", print_orientation: "landscape", definition: {} } });
    await restoreDailyRevision("assignment_roster", "00000000-0000-4000-8000-000000000101", 2);
    expect(request).toHaveBeenLastCalledWith(expect.stringMatching(/restore$/), expect.objectContaining({ method: "POST", body: JSON.stringify({ revision_number: 2 }) }));
  });
});
