import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SessionProfile } from "../auth/api";
import { OfficerHomePage } from "./OfficerHomePage";
import { fetchOfficerHomeSummary } from "./api";

vi.mock("./api", () => ({ fetchOfficerHomeSummary: vi.fn() }));

const profile: SessionProfile = {
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

beforeEach(() => {
  vi.mocked(fetchOfficerHomeSummary).mockResolvedValue({
    continueIncident: {
      incidentId: "00000000-0000-4000-8000-000000000010",
      incidentNumber: "2026-08-029",
      incidentName: "Fictional Training Incident",
      incidentDate: "2026-08-19",
      category: "training",
      location: "Training Hall",
      reportingOfficers: [{
        staffId: profile.staffId,
        displayName: profile.displayName,
      }],
      relationship: "reporting",
      progress: { code: "ready_to_review", label: "Ready to review", blockingCount: 0 },
      officerReportCount: 1,
      requiredPaperworkCount: 3,
      updatedAt: "2026-08-19T15:00:00Z",
    },
    recentIncidents: [],
    quickForms: [{
      templateId: "00000000-0000-4000-8000-000000000020",
      code: "form_005_409",
      name: "005/409 Incident Report",
      outputKind: "digital_document",
    }],
    countSheet: {
      recordId: "00000000-0000-4000-8000-000000000030",
      revision: 2,
      updatedAt: "2026-08-19T15:01:00Z",
    },
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("officer Home dashboard", () => {
  it("uses authenticated and server-authorized data rather than sample rows", async () => {
    render(
      <MemoryRouter>
        <OfficerHomePage profile={profile} today="2026-08-19" />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Officer Casey Morgan" })).toBeInTheDocument();
    expect(screen.getAllByText("2026-08-029").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Fictional Training Incident").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Ready to review").length).toBeGreaterThan(0);
    expect(screen.getByText("Officer reports")).toBeInTheDocument();
    expect(screen.getByText("Required paperwork")).toBeInTheDocument();
    expect(screen.getByText("005/409 Incident Report")).toBeInTheDocument();
    expect(screen.getByText("Stay safe. Stay focused. You’re making a difference.")).toBeInTheDocument();
    expect(screen.queryByText("Barracks 4 Fight")).not.toBeInTheDocument();
  });

  it("keeps the four primary officer actions prominent and dimensional", async () => {
    render(
      <MemoryRouter>
        <OfficerHomePage profile={profile} today="2026-08-19" />
      </MemoryRouter>,
    );
    await screen.findByRole("heading", { name: "Officer Casey Morgan" });
    const actions = screen.getByRole("region", { name: "Primary actions" });
    for (const label of [
      "New Incident Report",
      "Open Count Sheet",
      "Ask a Policy Question",
      "Open Forms Library",
    ]) {
      expect(within(actions).getByRole("link", { name: label })).toBeInTheDocument();
    }
    expect(within(actions).queryByText("01")).not.toBeInTheDocument();
    expect(within(actions).getByText("Saved · Revision 2")).toBeInTheDocument();
    expect(document.querySelector(".officer-home-continue-metrics")).not.toBeNull();
    expect(document.querySelector(".count-panel")).toBeNull();
  });

  it("preloads only responsive Home hero candidates while Home is mounted", async () => {
    const view = render(
      <MemoryRouter>
        <OfficerHomePage profile={profile} today="2026-08-19" />
      </MemoryRouter>,
    );
    await screen.findByRole("heading", { name: "Officer Casey Morgan" });

    const preloads = document.head.querySelectorAll('link[data-gow-home-hero-preload="true"]');
    expect(preloads).toHaveLength(3);
    expect(Array.from(preloads).map((link) => link.getAttribute("media"))).toEqual([
      "(min-width: 1440px)",
      "(min-width: 761px) and (max-width: 1439px)",
      "(max-width: 760px)",
    ]);
    expect(Array.from(preloads).every((link) => link.getAttribute("fetchpriority") === "high")).toBe(true);

    view.unmount();
    expect(document.head.querySelectorAll('link[data-gow-home-hero-preload="true"]')).toHaveLength(0);
  });

  it("renders a long authorized display name in full without substituting or truncating it", async () => {
    const longName = "Officer Alexandria Montgomery-Washington the Third";
    render(
      <MemoryRouter>
        <OfficerHomePage profile={{ ...profile, displayName: longName }} today="2026-08-19" />
      </MemoryRouter>,
    );

    const heading = await screen.findByRole("heading", { name: longName });
    expect(heading).toHaveTextContent(longName);
    expect(heading).not.toHaveAttribute("title");
  });

  it("renders honest empty states when the officer has no records", async () => {
    vi.mocked(fetchOfficerHomeSummary).mockResolvedValueOnce({
      continueIncident: null,
      recentIncidents: [],
      quickForms: [],
      countSheet: null,
    });
    render(
      <MemoryRouter>
        <OfficerHomePage profile={profile} today="2026-08-19" />
      </MemoryRouter>,
    );

    expect(await screen.findByText("No unfinished incidents")).toBeInTheDocument();
    expect(screen.getByText("No recent incidents are available.")).toBeInTheDocument();
    expect(screen.getByText("No approved quick forms are available.")).toBeInTheDocument();
  });
});
