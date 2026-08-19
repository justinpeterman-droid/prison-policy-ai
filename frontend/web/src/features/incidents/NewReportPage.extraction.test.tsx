import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
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

const INCIDENT_ID = "00000000-0000-4000-8000-000000000029";

function response(data: unknown, status = 200): Response {
  return new Response(JSON.stringify({ data }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function incidentRecord(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    incident_id: INCIDENT_ID,
    incident_number: "2026-08-029",
    incident_name: "Barracks 4 Fight",
    status: "in_progress",
    current_revision_number: 1,
    reporting_staff_ids: [PROFILE.staffId],
    reporting_officers: [
      { staff_id: PROFILE.staffId, display_name: PROFILE.displayName },
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
    ...overrides,
  };
}

/**
 * The extract and classify jobs write their result into a NEW incident revision
 * on the server. The workspace therefore has to re-read the incident once the
 * job succeeds, or the officer never sees the extracted facts and the next save
 * carries a stale base revision.
 */
function stubExtractJob(refreshed: Record<string, unknown>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      if (method === "POST" && url.includes("/jobs/")) {
        return response({
          job_id: "00000000-0000-4000-8000-000000000099",
          incident_id: INCIDENT_ID,
          job_type: "extract",
          state: "succeeded",
          stage: null,
          base_incident_revision: 1,
        });
      }
      if (method === "POST" && url.endsWith("/incidents")) {
        return response(incidentRecord(), 201);
      }
      if (method === "GET" && url.includes(`/incidents/${INCIDENT_ID}`)) {
        return response(refreshed);
      }
      return response({ items: [] });
    }),
  );
}

async function reachReviewFacts() {
  render(
    <MemoryRouter>
      <NewReportPage profile={PROFILE} />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole("button", { name: /continue to field notes/i }));
  // The notes label also wraps a character counter, so its text content is not
  // exactly the visible caption. Match on the caption instead.
  fireEvent.change(await screen.findByLabelText(/Officer field notes/), {
    target: { value: "Fictional field notes describing the incident." },
  });
  fireEvent.click(screen.getByRole("button", { name: /save and review facts/i }));
  await screen.findByText("Review the extracted facts");
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Review Facts after a completed extraction", () => {
  it("shows the facts the extract job saved on the server", async () => {
    stubExtractJob(
      incidentRecord({
        current_revision_number: 2,
        extracted_facts: { inmate_involved: "Roe, John ADC# 111111" },
      }),
    );

    await reachReviewFacts();
    fireEvent.click(screen.getByRole("button", { name: /review notes/i }));

    expect(await screen.findByLabelText("inmate involved")).toHaveValue(
      "Roe, John ADC# 111111",
    );
    expect(
      screen.queryByText(/no extracted facts have been saved yet/i),
    ).not.toBeInTheDocument();
  });

  it("confirms facts against the revision the extract job produced", async () => {
    stubExtractJob(
      incidentRecord({
        current_revision_number: 2,
        extracted_facts: { inmate_involved: "Roe, John ADC# 111111" },
      }),
    );

    await reachReviewFacts();
    fireEvent.click(screen.getByRole("button", { name: /review notes/i }));
    await screen.findByLabelText("inmate involved");
    fireEvent.click(screen.getByRole("button", { name: /confirm facts and continue/i }));

    await screen.findByText("Resolve missing information");
    const patch = vi
      .mocked(fetch)
      .mock.calls.find(([, init]) => init?.method === "PATCH");
    expect(patch).toBeDefined();
    const [, init] = patch!;
    // A stale base revision would silently lose the extraction to a conflict.
    expect(JSON.parse(String(init?.body)).base_revision_number).toBe(2);
    expect(JSON.parse(String(init?.body)).extracted_facts).toEqual({
      inmate_involved: "Roe, John ADC# 111111",
    });
  });
});
