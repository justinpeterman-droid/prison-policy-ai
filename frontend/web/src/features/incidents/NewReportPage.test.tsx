import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SessionProfile } from "../auth/api";
import { NewReportPage } from "./NewReportPage";

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

function response(data: unknown, status = 200): Response {
  return new Response(JSON.stringify({ data }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/incidents") && !url.includes("/jobs/")) {
        return response(
          {
            incident_id: "00000000-0000-4000-8000-000000000029",
            incident_number: "2026-08-029",
            incident_name: "Barracks 4 Fight",
            status: "in_progress",
            current_revision_number: 1,
            reporting_staff_ids: [PROFILE.staffId],
            reporting_officers: [
              {
                staff_id: PROFILE.staffId,
                display_name: PROFILE.displayName,
              },
            ],
            field_notes: "Fictional field notes.",
            incident_date: "2026-08-19",
            incident_time: "14:30:00",
            facility: "Fictional Unit",
            shift: "A",
            location: "Barracks 4",
            category: "inmate_fight",
            classification: {},
            extracted_facts: {},
            gap_answers: {},
            charges: [],
            validation: {},
            warnings: [],
            created_at: "2026-08-19T14:30:00Z",
            updated_at: "2026-08-19T14:30:00Z",
          },
          201,
        );
      }
      return response({ items: [] });
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Six-step New Report workflow", () => {
  it("shows all six guided stages without a technical AI dashboard", () => {
    render(
      <MemoryRouter>
        <NewReportPage profile={PROFILE} />
      </MemoryRouter>,
    );

    const workflow = screen.getByRole("list", { name: "Report workflow" });
    for (const label of [
      "Officers",
      "Field Notes",
      "Review Facts",
      "Missing Information",
      "Reports",
      "Forms & Export",
    ]) {
      expect(within(workflow).getByText(label)).toBeInTheDocument();
    }
    expect(screen.getByText(PROFILE.displayName)).toBeInTheDocument();
    expect(screen.queryByText(/token/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/model temperature/i)).not.toBeInTheDocument();
  });

  it("creates a saved incident and advances through the guided workspace", async () => {
    render(
      <MemoryRouter>
        <NewReportPage profile={PROFILE} />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Incident number"), {
      target: { value: "202608029" },
    });
    fireEvent.change(screen.getByLabelText("Incident name"), {
      target: { value: "Barracks 4 Fight" },
    });
    fireEvent.click(screen.getByRole("button", { name: /continue to field notes/i }));

    fireEvent.change(await screen.findByLabelText("Officer field notes"), {
      target: { value: "Fictional field notes describing the incident." },
    });
    fireEvent.click(screen.getByRole("button", { name: /save and review facts/i }));

    expect(await screen.findByText("Review the extracted facts")).toBeInTheDocument();
    expect(screen.getByText("2026-08-029")).toBeInTheDocument();
    expect(
      vi.mocked(fetch).mock.calls.some(([, init]) => init?.method === "POST"),
    ).toBe(true);
  });

  it("preserves visible notes when a save conflicts", async () => {
    vi.mocked(fetch).mockImplementationOnce(async () =>
      new Response(
        JSON.stringify({
          error: {
            code: "revision_conflict",
            message: "The incident changed; your local text has been preserved.",
            retryable: false,
            details: { current_revision_number: 2 },
          },
        }),
        { status: 409, headers: { "Content-Type": "application/json" } },
      ),
    );

    render(
      <MemoryRouter>
        <NewReportPage profile={PROFILE} />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: /continue to field notes/i }));
    const notes = await screen.findByLabelText("Officer field notes");
    fireEvent.change(notes, {
      target: { value: "Fictional text that must remain visible." },
    });
    fireEvent.click(screen.getByRole("button", { name: /save and review facts/i }));

    expect(
      await screen.findByText(/local text has been preserved/i),
    ).toBeInTheDocument();
    expect(notes).toHaveValue("Fictional text that must remain visible.");
    await waitFor(() => expect(screen.getByText("Unsaved changes")).toBeInTheDocument());
  });
});
