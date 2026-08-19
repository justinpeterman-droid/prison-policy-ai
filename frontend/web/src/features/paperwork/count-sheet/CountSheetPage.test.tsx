import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SessionProfile } from "../../auth/api";
import { CountSheetPage } from "./CountSheetPage";
import { calculateCountTotals, createBlankCountPayload } from "./calculations";
import type { CountSheetStructure } from "./types";

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

const STRUCTURE: CountSheetStructure = {
  schema_version: 1,
  title: "North Central Unit Count Sheet",
  columns: ["1", "2", "Iso", "Inf"],
  areas: ["A/W Office", "Chow Hall"],
  operational_fields: [
    "on_site",
    "gate_pass",
    "transfers",
    "court",
    "hospital",
    "furlough",
    "other",
  ],
  attachment_reminders: ["court", "hospital", "furlough"],
};

function apiResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify({ data }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderPage() {
  return render(
    <MemoryRouter>
      <CountSheetPage profile={PROFILE} />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.stubGlobal("print", vi.fn());
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/paperwork/count-sheets/structure")) {
        return apiResponse(STRUCTURE);
      }
      if (url.includes("/paperwork?kind=count_sheet")) {
        return apiResponse({ items: [], next_cursor: null });
      }
      if (url.endsWith("/paperwork/count-sheets") && init?.method === "POST") {
        const body = JSON.parse(String(init.body));
        return apiResponse(
          {
            record_id: "00000000-0000-4000-8000-000000000101",
            kind: "count_sheet",
            work_date: body.work_date,
            shift: body.shift,
            current_revision_number: 1,
            payload: body.payload,
            validation: calculateCountTotals(STRUCTURE, body.payload),
            created_by_staff_member_id: PROFILE.staffId,
            last_editor_staff_member_id: PROFILE.staffId,
            created_at: "2026-08-19T15:00:00Z",
            updated_at: "2026-08-19T15:00:00Z",
          },
          201,
        );
      }
      if (url.endsWith("/actions") && init?.method === "POST") {
        return apiResponse({
          recorded: true,
          record_id: "00000000-0000-4000-8000-000000000101",
          kind: "count_sheet",
          revision_number: 1,
          action: "print",
        });
      }
      throw new Error(`Unhandled test request: ${url}`);
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("NCU Days Count workspace", () => {
  it("renders the approved grid, calculates totals, and shows a signed mismatch", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "NCU Days Count" })).toBeInTheDocument();
    expect(screen.getByText("North Central Unit Count Sheet")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Area" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Iso" })).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "A/W Office" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("A/W Office, column 1"), {
      target: { value: "4" },
    });
    fireEvent.change(screen.getByLabelText("In housing, column 1"), {
      target: { value: "6" },
    });
    fireEvent.change(screen.getByLabelText("Operational total: on site"), {
      target: { value: "8" },
    });

    expect(screen.getByText(/totals differ by 2/i)).toBeInTheDocument();
    expect(screen.getByText("Housing total 10")).toBeInTheDocument();
    expect(screen.getByText("Operational total 8")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Operational total: on site"), {
      target: { value: "10" },
    });
    expect(screen.getByText(/count reconciles/i)).toBeInTheDocument();
  });

  it("supports arrow and Enter movement through the official grid", async () => {
    renderPage();
    const first = await screen.findByLabelText("A/W Office, column 1");
    const right = screen.getByLabelText("A/W Office, column 2");
    const below = screen.getByLabelText("Chow Hall, column 2");

    first.focus();
    fireEvent.keyDown(first, { key: "ArrowRight" });
    expect(right).toHaveFocus();
    fireEvent.keyDown(right, { key: "Enter" });
    expect(below).toHaveFocus();
    fireEvent.keyDown(below, { key: "Enter", shiftKey: true });
    expect(right).toHaveFocus();
  });

  it("saves visible values before recording and opening print", async () => {
    renderPage();
    const field = await screen.findByLabelText("A/W Office, column 1");
    fireEvent.change(field, { target: { value: "4" } });
    fireEvent.change(screen.getByLabelText("In housing, column 1"), {
      target: { value: "6" },
    });
    fireEvent.change(screen.getByLabelText("Operational total: on site"), {
      target: { value: "10" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Save Count Sheet" }));
    expect(await screen.findByText("Saved")).toBeInTheDocument();
    expect(field).toHaveValue("4");

    fireEvent.click(screen.getByRole("button", { name: "Print Count Sheet" }));
    await waitFor(() => expect(window.print).toHaveBeenCalledTimes(1));
    expect(
      vi.mocked(fetch).mock.calls.some(([input]) => String(input).endsWith("/actions")),
    ).toBe(true);
  });

  it("starts from a blank server-defined payload without inventing values", async () => {
    renderPage();
    await screen.findByRole("heading", { name: "NCU Days Count" });
    const blank = createBlankCountPayload(STRUCTURE);

    expect(screen.getByLabelText("A/W Office, column 1")).toHaveValue("");
    expect(screen.getByLabelText("In housing, column 1")).toHaveValue("");
    expect(blank.cells["A/W Office"]["1"]).toBeNull();
    expect(blank.operational.on_site).toBeNull();
  });
});
