import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DailyRecord } from "../api";
import * as paperworkApi from "../api";
import { createEmptyMetalPayload, type MetalPayload } from "./model";
import { MetalDetectorEditor } from "./MetalDetectorEditor";


vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return { ...actual, saveDailyRecord: vi.fn(), createDailyRecord: vi.fn(), recordDailyAction: vi.fn() };
});

function record(payload = createEmptyMetalPayload("2026-08-20", "D")): DailyRecord {
  return { recordId: "00000000-0000-4000-8000-000000000601", kind: "metal_detector_test", title: "Daily Walk-Through Metal Detector Testing", workDate: "2026-08-20", shift: "D", revision: 1, state: "saved", warningCount: 0, updatedAt: "2026-08-20T14:00:00Z", payload, validation: { failed_test_count: 0 }, template: { schemaVersion: 1, title: "Daily Walk-Through Metal Detector Testing", printOrientation: "landscape", definition: {} } };
}

beforeEach(() => vi.clearAllMocks());

describe("Walk-Through Metal Detector editor", () => {
  it("renders detectors 1-11 by seven approved positions and supports keyboard matrix navigation", () => {
    render(<MemoryRouter><MetalDetectorEditor workDate="2026-08-20" shift="D" record={record()} onRecordChange={vi.fn()} searchStaff={vi.fn().mockResolvedValue([])} /></MemoryRouter>);
    const matrix = screen.getByRole("table", { name: "Detector test matrix" });
    expect(within(matrix).getAllByRole("columnheader").slice(1).map((item) => item.textContent)).toEqual(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]);
    expect(within(matrix).getAllByRole("rowheader")).toHaveLength(7);
    const first = screen.getByLabelText("Detector 1 Position 1");
    const next = screen.getByLabelText("Detector 2 Position 1");
    first.focus();
    fireEvent.keyDown(first, { key: "ArrowRight" });
    expect(next).toHaveFocus();
  });

  it("bulk-marks a detector P and blocks a failed detector without corrective action", async () => {
    const user = userEvent.setup();
    const source = record();
    const savedPayload = createEmptyMetalPayload("2026-08-20", "D");
    savedPayload.detectors[0].tests[0].result = "F";
    savedPayload.detectors[0].corrective_action = "Removed from service and notified maintenance.";
    const saved = record(savedPayload);
    vi.mocked(paperworkApi.saveDailyRecord).mockResolvedValue(saved);
    const onRecordChange = vi.fn();
    render(<MemoryRouter><MetalDetectorEditor workDate="2026-08-20" shift="D" record={source} onRecordChange={onRecordChange} searchStaff={vi.fn().mockResolvedValue([])} /></MemoryRouter>);

    await user.click(screen.getByRole("button", { name: "Mark Detector 1 Pass" }));
    expect(screen.getByLabelText("Detector 1 Position 7")).toHaveValue("P");
    await user.selectOptions(screen.getByLabelText("Detector 1 Position 1"), "F");
    await user.click(screen.getByRole("button", { name: "Save detector test" }));
    expect(screen.getByRole("alert")).toHaveTextContent(/Detector 1.*corrective action/i);
    expect(paperworkApi.saveDailyRecord).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText("Detector 1 corrective action"), "Removed from service and notified maintenance.");
    await user.type(screen.getByLabelText("Detector 1 location"), "Front entrance");
    await user.type(screen.getByLabelText("Detector 1 equipment identifier"), "Fixture A");
    await user.click(screen.getByRole("button", { name: "Save detector test" }));
    await waitFor(() => expect(paperworkApi.saveDailyRecord).toHaveBeenCalled());
    const submitted = vi.mocked(paperworkApi.saveDailyRecord).mock.calls[0][0].payload as MetalPayload;
    expect(submitted.detectors[0].location).toBe("Front entrance");
    expect(onRecordChange).toHaveBeenCalledWith(saved);
  });

  it("renders sign-off pickers, mobile detector navigation, and the official print guidance", () => {
    render(<MemoryRouter><MetalDetectorEditor workDate="2026-08-20" shift="D" record={record()} onRecordChange={vi.fn()} searchStaff={vi.fn().mockResolvedValue([])} /></MemoryRouter>);
    expect(screen.getByRole("combobox", { name: "Tested by" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Reviewed by" })).toBeInTheDocument();
    expect(screen.getByLabelText("Mobile detector")).toHaveTextContent("Detector 11");
    const print = screen.getByTestId("metal-detector-print");
    expect(print).toHaveTextContent("P = Pass");
    expect(print).toHaveTextContent("Comments, including Corrective Action Taken");
    expect(print).toHaveTextContent("Location / Equipment Identifier");
    expect(print).toHaveTextContent("Distribution");
  });
});
