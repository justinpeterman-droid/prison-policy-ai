import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { App } from "./App";
import type { SessionProfile } from "./features/auth/api";

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

function renderApp(profile: SessionProfile = PROFILE) {
  return render(
    <MemoryRouter>
      <App profile={profile} />
    </MemoryRouter>,
  );
}

afterEach(cleanup);

describe("Guided Operations officer home", () => {
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
    expect(screen.getByText("A Shift")).toBeInTheDocument();
    expect(screen.getByText("CM")).toBeInTheDocument();
    expect(screen.queryByText("Officer Peterman")).not.toBeInTheDocument();
  });

  it("keeps the four primary daily actions easy to find", () => {
    renderApp();

    for (const label of PRIMARY_ACTIONS) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
  });

  it("shows incident work by official incident number", () => {
    renderApp();

    expect(screen.getAllByText("2026-08-029").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Barracks 4 Fight").length).toBeGreaterThan(0);
    expect(screen.getByText("Continue Your Work")).toBeInTheDocument();
    expect(screen.getByText("Recent Incidents")).toBeInTheDocument();
  });

  it("presents daily paperwork and forms without crowding the primary actions", () => {
    renderApp();

    expect(screen.getByText("Your Daily Checklist")).toBeInTheDocument();
    expect(screen.getByText("Frequently Used Forms")).toBeInTheDocument();
    expect(screen.getByText("Complete Assignment Roster")).toBeInTheDocument();
    expect(screen.getByText("Complete Uniform Inspection Log")).toBeInTheDocument();
  });

  it("exposes useful connection and save state in plain language", () => {
    renderApp();

    expect(screen.getByText("Online")).toBeInTheDocument();
    expect(screen.getByText(/Last synced/i)).toBeInTheDocument();
    expect(screen.getByText(/All changes saved/i)).toBeInTheDocument();
  });
});
