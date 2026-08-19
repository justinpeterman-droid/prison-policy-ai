import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import type { SessionProfile } from "../features/auth/api";
import { OfficerWorkspaceLayout } from "./OfficerWorkspaceLayout";

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

afterEach(cleanup);

describe("Officer Workspace layout", () => {
  it("keeps the approved officer navigation and authenticated identity", () => {
    render(
      <MemoryRouter initialEntries={["/forms"]}>
        <Routes>
          <Route element={<OfficerWorkspaceLayout profile={profile} />}>
            <Route path="forms" element={<h1>Forms content</h1>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    const navigation = screen.getByRole("navigation", { name: "Officer navigation" });
    for (const label of [
      "Home",
      "New Report",
      "Reports",
      "Policy Expert",
      "Forms Library",
      "Account",
    ]) {
      expect(within(navigation).getByRole("link", { name: label })).toBeInTheDocument();
    }
    expect(screen.getAllByText("Officer Casey Morgan").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Forms content" })).toBeInTheDocument();
    expect(within(navigation).getByRole("link", { name: "Forms Library" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("does not expose Administration to an officer role", () => {
    render(
      <MemoryRouter>
        <Routes>
          <Route element={<OfficerWorkspaceLayout profile={profile} />}>
            <Route index element={<p>Home</p>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.queryByRole("link", { name: "Administration" })).not.toBeInTheDocument();
  });
});
