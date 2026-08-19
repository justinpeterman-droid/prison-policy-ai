import { describe, expect, it, vi } from "vitest";
import { fetchOfficerHomeSummary, parseOfficerHomeSummary } from "./api";

const mocks = vi.hoisted(() => ({ requestPath: "" }));

vi.mock("../../api/client", () => ({
  webApiRequest: vi.fn(async (path: string) => {
    mocks.requestPath = path;
    return {
      continue_incident: null,
      recent_incidents: [],
      quick_forms: [],
      count_sheet: null,
    };
  }),
}));

describe("officer Home summary API", () => {
  it("parses content-free incident and utility metadata", () => {
    const result = parseOfficerHomeSummary({
      continue_incident: {
        incident_id: "00000000-0000-4000-8000-000000000001",
        incident_number: "2026-08-029",
        incident_name: "Fictional Training Incident",
        incident_date: "2026-08-19",
        category: "training",
        location: "Training Hall",
        reporting_officers: [{
          staff_id: "00000000-0000-4000-8000-000000000002",
          display_name: "Officer Casey Morgan",
        }],
        relationship: "reporting",
        progress: { code: "ready_to_review", label: "Ready to review", blocking_count: 0 },
        officer_report_count: 1,
        required_paperwork_count: 3,
        updated_at: "2026-08-19T15:00:00Z",
      },
      recent_incidents: [],
      quick_forms: [{
        template_id: "00000000-0000-4000-8000-000000000003",
        code: "form_005_409",
        name: "005/409 Incident Report",
        output_kind: "digital_document",
      }],
      count_sheet: {
        record_id: "00000000-0000-4000-8000-000000000004",
        current_revision_number: 2,
        updated_at: "2026-08-19T15:01:00Z",
      },
    });

    expect(result.continueIncident?.incidentNumber).toBe("2026-08-029");
    expect(result.quickForms[0]?.name).toBe("005/409 Incident Report");
    expect(result.countSheet?.revision).toBe(2);
    expect(JSON.stringify(result)).not.toContain("field_notes");
    expect(JSON.stringify(result)).not.toContain("narrative");
  });

  it("builds encoded date and shift parameters", async () => {
    await fetchOfficerHomeSummary("2026-08-19", "A Shift");
    expect(mocks.requestPath).toContain("date=2026-08-19");
    expect(mocks.requestPath).toContain("shift=A+Shift");
  });
});
