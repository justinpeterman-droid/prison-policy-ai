import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "./App";

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

describe("Guided Operations officer home", () => {
  it("renders the approved six-item officer navigation", () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );

    for (const label of OFFICER_NAVIGATION) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
  });

  it("keeps the four primary daily actions easy to find", () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );

    for (const label of PRIMARY_ACTIONS) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
  });

  it("shows incident work by official incident number", () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByText("2026-08-029")).toBeInTheDocument();
    expect(screen.getByText("Barracks 4 Fight")).toBeInTheDocument();
  });
});
