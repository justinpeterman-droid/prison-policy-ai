import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import type { SessionProfile } from "./features/auth/api";
import { fetchOfficerHomeSummary } from "./features/dashboard/api";

vi.mock("./features/dashboard/api", () => ({
  fetchOfficerHomeSummary: vi.fn(async () => ({
    continueIncident: null,
    recentIncidents: [],
    quickForms: [],
    countSheet: null,
  })),
}));

const OFFICER_NAVIGATION = [
  "Home",
  "New Report",
  "Reports",
  "Policy Expert",
  "Forms Library",
  "Account",
];

const PRIMARY_ACTIONS = [
  "Start New Incident",
  "Open Count Sheet",
  "Ask a Policy Question",
  "Open Forms Library",
];

const PROFILE: SessionProfile = {
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

function renderApp(path = "/", profile: SessionProfile = PROFILE) {
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

describe("Guided Operations officer application", () => {
  it("renders the approved six-item officer navigation", () => {
    renderApp();

    const navigation = screen.getByRole("navigation", { name: "Officer navigation" });
    for (const label of OFFICER_NAVIGATION) {
      expect(within(navigation).getByRole("link", { name: label })).toBeInTheDocument();
    }
    expect(within(navigation).queryByText("Administration")).not.toBeInTheDocument();
  });

  it("uses the authenticated employee profile in the shell", () => {
    renderApp();

    expect(screen.getAllByText("Officer Casey Morgan").length).toBeGreaterThan(0);
    expect(screen.getAllByText("A Shift").length).toBeGreaterThan(0);
    expect(screen.getByText("CM")).toBeInTheDocument();
    expect(screen.queryByText("Officer Peterman")).not.toBeInTheDocument();
  });

  it("keeps the four primary daily actions easy to find", () => {
    renderApp();

    for (const label of PRIMARY_ACTIONS) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
    expect(fetchOfficerHomeSummary).toHaveBeenCalled();
  });

  it("routes Policy Expert to the real citation workspace", () => {
    renderApp("/policy-expert");

    expect(screen.getByRole("heading", { name: "Policy Expert" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ask Policy Expert" })).toBeInTheDocument();
    expect(screen.queryByText(/scheduled in the next product milestone/i)).not.toBeInTheDocument();
  });

  it("routes Forms Library to the real approved-form workspace", () => {
    renderApp("/forms");

    expect(screen.getByRole("heading", { name: "Forms Library" })).toBeInTheDocument();
    expect(screen.getByRole("searchbox", { name: "Search forms" })).toBeInTheDocument();
    expect(screen.queryByText(/scheduled in the next product milestone/i)).not.toBeInTheDocument();
  });

  it("routes Account to the individual security workspace", () => {
    renderApp("/account");

    expect(screen.getByRole("heading", { name: "My Account" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Active browser sessions" })).toBeInTheDocument();
    expect(screen.queryByText(/scheduled in the next product milestone/i)).not.toBeInTheDocument();
  });

  it("exposes connection state without claiming fictional synchronization", () => {
    renderApp();

    expect(screen.getByText("Online")).toBeInTheDocument();
    expect(screen.getByText("Secure browser session")).toBeInTheDocument();
    expect(screen.queryByText(/Last synced 2 minutes ago/i)).not.toBeInTheDocument();
  });
});
