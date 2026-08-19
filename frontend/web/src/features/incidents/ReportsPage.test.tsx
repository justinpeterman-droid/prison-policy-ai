import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ReportsPage } from "./ReportsPage";

function ok(data: unknown): Response {
  return new Response(JSON.stringify({ data }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

const INCIDENTS = {
  items: [
    {
      incident_id: "00000000-0000-4000-8000-000000000029",
      incident_number: "2026-08-029",
      incident_name: "Barracks 4 Fight",
      incident_date: "2026-08-19",
      category: "inmate_fight",
      location: "Barracks 4",
      reporting_officers: [
        {
          staff_id: "00000000-0000-4000-8000-000000000002",
          display_name: "Officer Casey Morgan",
        },
      ],
      relationship: "reporting",
      progress: {
        code: "ready_to_review",
        label: "Ready to Review",
        blocking_count: 0,
      },
      officer_report_count: 2,
      required_paperwork_count: 4,
      updated_at: "2026-08-19T14:40:00Z",
    },
  ],
  next_cursor: null,
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ok(INCIDENTS)),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Reports incident library", () => {
  it("organizes work by official incident number and name", async () => {
    render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText("2026-08-029")).toBeInTheDocument();
    expect(screen.getByText("Barracks 4 Fight")).toBeInTheDocument();
    expect(screen.getByText("Ready to Review")).toBeInTheDocument();
    expect(screen.getByText("2 officer reports")).toBeInTheDocument();
    expect(screen.getByText("4 required items")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /open incident 2026-08-029/i }),
    ).toHaveAttribute(
      "href",
      "/reports/00000000-0000-4000-8000-000000000029",
    );
  });

  it("sends search and relationship filters to the server", async () => {
    render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>,
    );
    await screen.findByText("2026-08-029");

    fireEvent.change(screen.getByLabelText("Search incidents"), {
      target: { value: "contraband" },
    });
    fireEvent.change(screen.getByLabelText("Incident relationship"), {
      target: { value: "prepared" },
    });

    await waitFor(() => {
      const calls = vi.mocked(fetch).mock.calls;
      expect(
        calls.some(([url]) =>
          String(url).includes("q=contraband") &&
          String(url).includes("relationship=prepared"),
        ),
      ).toBe(true);
    });
  });

  it("never asks officers to manually set a records status", async () => {
    render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>,
    );
    await screen.findByText("2026-08-029");

    expect(screen.queryByLabelText(/status/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/change status/i)).not.toBeInTheDocument();
  });
});
