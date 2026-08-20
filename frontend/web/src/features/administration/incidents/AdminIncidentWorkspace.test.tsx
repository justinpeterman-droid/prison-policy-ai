import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AdminIncidentWorkspace } from "./AdminIncidentWorkspace";
import * as adminIncidentApi from "./api";

vi.mock("../../incidents/DocumentStudioPage", () => ({
  DocumentStudioPage: () => <div>Officer Document Studio</div>,
}));

vi.mock("./api", () => ({
  getAdminIncidentDetail: vi.fn(),
  changeAdminRecordsStatus: vi.fn(),
  restoreAdminIncident: vi.fn(),
  transferAdminReport: vi.fn(),
}));

const INCIDENT_ID = "00000000-0000-4000-8000-000000000910";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("admin incident workspace", () => {
  it("keeps attribution visible and separates records status from officer progress", async () => {
    vi.mocked(adminIncidentApi.getAdminIncidentDetail).mockResolvedValue({
      incidentId: INCIDENT_ID,
      incidentNumber: "2026-08-029",
      incidentName: "Fictional Training Incident",
      recordsStatus: "in_progress",
      currentRevisionNumber: 4,
      reportingOfficers: [{ staffId: "staff-1", displayName: "Officer Casey Morgan" }],
      preparers: [{ staffId: "staff-2", displayName: "Officer Riley Stone" }],
      reports: [{
        reportId: "00000000-0000-4000-8000-000000000920",
        reportType: "officer_report",
        status: "draft",
        currentRevisionNumber: 2,
        reportingOfficer: { staffId: "staff-1", displayName: "Officer Casey Morgan" },
        preparer: { staffId: "staff-2", displayName: "Officer Riley Stone" },
      }],
    });

    render(
      <MemoryRouter initialEntries={[`/admin/incidents/${INCIDENT_ID}`]}>
        <Routes>
          <Route path="/admin/incidents/:incidentId" element={<AdminIncidentWorkspace />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("2026-08-029")).toBeInTheDocument();
    expect(screen.getByRole("note", { name: "Administrator attribution notice" })).toBeInTheDocument();
    expect(screen.getByLabelText("Records status")).toHaveValue("in_progress");
    expect(screen.getByText("Revision 4")).toBeInTheDocument();
    expect(screen.getByText("Officer Document Studio")).toBeInTheDocument();
  });

  it("opens a purpose-scoped confirmation before revision restore", async () => {
    vi.mocked(adminIncidentApi.getAdminIncidentDetail).mockResolvedValue({
      incidentId: INCIDENT_ID,
      incidentNumber: "2026-08-029",
      incidentName: "Fictional Training Incident",
      recordsStatus: "in_progress",
      currentRevisionNumber: 4,
      reportingOfficers: [],
      preparers: [],
      reports: [],
    });

    render(
      <MemoryRouter initialEntries={[`/admin/incidents/${INCIDENT_ID}`]}>
        <Routes>
          <Route path="/admin/incidents/:incidentId" element={<AdminIncidentWorkspace />} />
        </Routes>
      </MemoryRouter>,
    );

    await screen.findByText("2026-08-029");
    fireEvent.change(screen.getByLabelText("Restore revision"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Restore reason"), { target: { value: "Correcting fictional training data" } });
    fireEvent.click(screen.getByRole("button", { name: "Restore revision" }));

    expect(screen.getByRole("heading", { name: "Confirm incident restore" })).toBeInTheDocument();
    expect(adminIncidentApi.restoreAdminIncident).not.toHaveBeenCalled();
  });
});
