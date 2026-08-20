import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { listAdminIncidents } from "../api";
import { AdminIncidentsPage } from "./AdminIncidentsPage";

vi.mock("../api", () => ({ listAdminIncidents: vi.fn() }));

describe("administrator incident results", () => {
  beforeEach(() => {
    vi.mocked(listAdminIncidents).mockResolvedValue({
      items: [{
        incidentId: "00000000-0000-4000-8000-000000000029",
        incidentNumber: "2026-08-029",
        incidentName: "Fictional Barracks Review",
        incidentDate: "2026-08-20",
        category: "conduct",
        facility: "Fictional Facility",
        location: "Barracks 4",
        shift: "D",
        recordsStatus: "in_progress",
        reportingOfficers: [{ staffId: "00000000-0000-4000-8000-000000000002", displayName: "Officer Casey Morgan" }],
        preparers: [],
        progress: { code: "needs_information", label: "Needs information", blockingCount: 1 },
        officerReportCount: 1,
        requiredPaperworkCount: 2,
        updatedAt: "2026-08-20T14:00:00Z",
      }],
      nextCursor: null,
    });
  });

  it("uses the canonical chevron-navigation row without replacing the admin grid contract", async () => {
    render(<MemoryRouter><AdminIncidentsPage /></MemoryRouter>);

    const row = await screen.findByRole("link", { name: /2026-08-029.*Fictional Barracks Review/i });
    expect(row).toHaveClass("gow-list-row", "gow-list-row--navigation", "admin-table-row", "admin-incidents-grid");
    expect(row).toHaveAttribute("href", "/admin/incidents/00000000-0000-4000-8000-000000000029");
    expect(row.querySelector(".admin-row-arrow")).toBeInTheDocument();
  });
});
