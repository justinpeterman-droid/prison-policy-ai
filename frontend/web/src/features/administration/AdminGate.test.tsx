import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../../App";
import type { SessionProfile } from "../auth/api";
import * as adminApi from "./api";

vi.mock("../dashboard/api", () => ({
  fetchOfficerHomeSummary: vi.fn(async () => ({
    continueIncident: null,
    recentIncidents: [],
    quickForms: [],
    countSheet: null,
  })),
}));

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    getAdminElevation: vi.fn(),
    enterAdminElevation: vi.fn(),
    getAdminOverview: vi.fn(),
  };
});

const USER: SessionProfile = {
  accountId: "00000000-0000-4000-8000-000000000001",
  staffId: "00000000-0000-4000-8000-000000000002",
  sessionId: "00000000-0000-4000-8000-000000000003",
  employeeNumber: "F-1001",
  displayName: "Officer Casey Morgan",
  rank: "Officer",
  shift: "A",
  role: "user",
  mustChangePin: false,
};

const ADMIN: SessionProfile = {
  ...USER,
  accountId: "00000000-0000-4000-8000-000000000010",
  staffId: "00000000-0000-4000-8000-000000000011",
  sessionId: "00000000-0000-4000-8000-000000000012",
  employeeNumber: "A-9001",
  displayName: "Captain Jordan Blake",
  rank: "Captain",
  role: "admin",
};

function renderApp(path: string, profile: SessionProfile) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App profile={profile} />
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Administrator Command Center gate", () => {
  it("never exposes Administration to a normal officer", () => {
    renderApp("/", USER);
    expect(screen.queryByRole("link", { name: "Administration" })).not.toBeInTheDocument();
  });

  it("shows Administration separately for administrator accounts", () => {
    renderApp("/", ADMIN);
    expect(screen.getByRole("link", { name: "Administration" })).toBeInTheDocument();
  });

  it("renders not found for a user who directly enters an admin route", () => {
    renderApp("/admin/overview", USER);
    expect(screen.getByRole("heading", { name: "Workspace page not found" })).toBeInTheDocument();
    expect(screen.queryByText("Operational Command Center")).not.toBeInTheDocument();
  });

  it("prompts an admin for PIN elevation without losing the requested destination", async () => {
    vi.mocked(adminApi.getAdminElevation).mockResolvedValue({
      elevated: false,
      elevationExpiresAt: null,
    });
    vi.mocked(adminApi.enterAdminElevation).mockResolvedValue({
      elevated: true,
      elevationExpiresAt: "2026-08-20T01:30:00Z",
    });
    vi.mocked(adminApi.getAdminOverview).mockResolvedValue({
      todaysPaperwork: {
        assignmentRoster: { status: "not_started", recordId: null, updatedAt: null },
        uniformInspection: { status: "not_started", recordId: null, updatedAt: null },
      },
      incidentsNeedingAttention: [],
      accountConditions: { locked: 0, deactivated: 0, temporaryPin: 0 },
      systemAvailability: {
        database: "Operational",
        queue: "Operational",
        ai: "Operational",
        policyExpert: "Operational",
        backupRestore: "Unavailable",
      },
      recentAdministrativeActivity: [],
    });

    renderApp("/admin/overview", ADMIN);
    expect(await screen.findByRole("heading", { name: "Administrator confirmation" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Administrator PIN"), { target: { value: "A12345" } });
    fireEvent.click(screen.getByRole("button", { name: "Enter Admin Center" }));

    await waitFor(() => expect(adminApi.enterAdminElevation).toHaveBeenCalledWith("A12345"));
    expect(await screen.findByRole("heading", { name: "Operational Command Center" })).toBeInTheDocument();
    const adminNav = screen.getByRole("navigation", { name: "Administration navigation" });
    for (const label of [
      "Overview",
      "All Incidents",
      "Paperwork Center",
      "Accounts & Staff",
      "Audit Log",
      "System Health",
      "Review Lab",
    ]) {
      expect(within(adminNav).getByRole("link", { name: label })).toBeInTheDocument();
    }
  });
});
