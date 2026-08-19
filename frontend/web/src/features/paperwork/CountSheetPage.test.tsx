import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { WebApiError } from "../../api/client";
import type { SessionProfile } from "../auth/api";
import { CountSheetPage } from "./CountSheetPage";
import {
  createCountSheet,
  fetchCountDefinition,
  lookupCountSheet,
  saveCountSheet,
} from "./api";
import type { CountSheetDefinition } from "./counts";

vi.mock("./api", () => ({
  fetchCountDefinition: vi.fn(),
  lookupCountSheet: vi.fn(),
  createCountSheet: vi.fn(),
  saveCountSheet: vi.fn(),
}));

const definition: CountSheetDefinition = {
  schemaVersion: 1,
  title: "Fictional Count Sheet",
  rows: [{ id: "alpha", label: "Housing Alpha", section: "in_housing" }],
  columns: [
    { id: "assigned", label: "Assigned" },
    { id: "present", label: "Present" },
  ],
  operationalTotalColumn: "present",
};

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
  vi.mocked(fetchCountDefinition).mockResolvedValue({
    definition,
    sha256: "a".repeat(64),
  });
  vi.mocked(lookupCountSheet).mockResolvedValue(null);
  vi.mocked(createCountSheet).mockResolvedValue({
    recordId: "00000000-0000-4000-8000-000000000010",
    recordDate: "2026-08-19",
    shift: "A",
    revision: 1,
    definitionSha256: "a".repeat(64),
    values: { alpha: { present: 9 } },
    expectedOperationalTotal: 10,
    updatedAt: "2026-08-19T15:00:00Z",
  });
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe("Count Sheet page", () => {
  it("creates a new revisioned Count Sheet and keeps the signed mismatch visible", async () => {
    render(<CountSheetPage profile={profile} today="2026-08-19" />);
    const present = await screen.findByRole("textbox", { name: "Housing Alpha Present" });
    fireEvent.change(present, { target: { value: "9" } });
    fireEvent.change(screen.getByRole("textbox", { name: "Expected operational total" }), {
      target: { value: "10" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save count" }));

    await waitFor(() => expect(createCountSheet).toHaveBeenCalledWith(expect.objectContaining({
      shift: "A",
      recordDate: "2026-08-19",
      values: { alpha: { present: 9 } },
      expectedOperationalTotal: 10,
    })));
    expect(screen.getByText("Difference: -1")).toBeInTheDocument();
  });

  it("autosaves an existing record after sixty seconds of inactivity", async () => {
    vi.useFakeTimers();
    vi.mocked(lookupCountSheet).mockResolvedValueOnce({
      recordId: "00000000-0000-4000-8000-000000000010",
      recordDate: "2026-08-19",
      shift: "A",
      revision: 2,
      definitionSha256: "a".repeat(64),
      values: { alpha: { present: 8 } },
      expectedOperationalTotal: 8,
      updatedAt: "2026-08-19T15:00:00Z",
    });
    vi.mocked(saveCountSheet).mockResolvedValue({
      recordId: "00000000-0000-4000-8000-000000000010",
      recordDate: "2026-08-19",
      shift: "A",
      revision: 3,
      definitionSha256: "a".repeat(64),
      values: { alpha: { present: 9 } },
      expectedOperationalTotal: 8,
      updatedAt: "2026-08-19T15:01:00Z",
    });
    render(<CountSheetPage profile={profile} today="2026-08-19" />);
    const present = await screen.findByRole("textbox", { name: "Housing Alpha Present" });
    fireEvent.change(present, { target: { value: "9" } });

    await vi.advanceTimersByTimeAsync(60_000);

    expect(saveCountSheet).toHaveBeenCalledWith(expect.objectContaining({
      recordId: "00000000-0000-4000-8000-000000000010",
      revision: 2,
      reason: "autosave",
      values: { alpha: { present: 9 } },
    }));
  });

  it("preserves local entries and explains a stale revision conflict", async () => {
    vi.mocked(lookupCountSheet).mockResolvedValueOnce({
      recordId: "00000000-0000-4000-8000-000000000010",
      recordDate: "2026-08-19",
      shift: "A",
      revision: 2,
      definitionSha256: "a".repeat(64),
      values: { alpha: { present: 8 } },
      expectedOperationalTotal: 8,
      updatedAt: "2026-08-19T15:00:00Z",
    });
    vi.mocked(saveCountSheet).mockRejectedValueOnce(new WebApiError({
      code: "revision_conflict",
      message: "The Count Sheet changed; reload before saving.",
      status: 409,
    }));
    render(<CountSheetPage profile={profile} today="2026-08-19" />);
    const present = await screen.findByRole("textbox", { name: "Housing Alpha Present" });
    fireEvent.change(present, { target: { value: "9" } });
    fireEvent.click(screen.getByRole("button", { name: "Save count" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "changed on the server",
    );
    expect(present).toHaveValue("9");
  });

  it("fails closed when the approved definition is unavailable", async () => {
    vi.mocked(fetchCountDefinition).mockRejectedValueOnce(new Error(
      "The approved NCU Days Count template has not been published.",
    ));
    render(<CountSheetPage profile={profile} today="2026-08-19" />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "approved NCU Days Count template",
    );
    expect(screen.queryByRole("button", { name: "Save count" })).not.toBeInTheDocument();
  });
});
