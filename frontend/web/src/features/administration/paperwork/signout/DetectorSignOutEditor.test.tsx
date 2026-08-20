import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DailyRecord } from "../api";
import * as paperworkApi from "../api";
import { createEmptySignOutPayload, parseSignOutPayload } from "./model";
import { DetectorSignOutEditor } from "./DetectorSignOutEditor";

vi.mock("../api", async () => { const actual = await vi.importActual<typeof import("../api")>("../api"); return { ...actual, saveDailyRecord: vi.fn(), createDailyRecord: vi.fn(), recordDailyAction: vi.fn() }; });
function record(): DailyRecord { return { recordId: "00000000-0000-4000-8000-000000000901", kind: "detector_sign_out", title: "Handheld Metal Detector Sign-Out", workDate: "2026-08-20", shift: "D", revision: 1, state: "saved", warningCount: 0, updatedAt: "2026-08-20T14:00:00Z", payload: createEmptySignOutPayload("2026-08-20", "D"), validation: { incomplete_count: 9 }, template: { schemaVersion: 1, title: "Handheld Metal Detector Sign-Out", printOrientation: "portrait", definition: {} } }; }
beforeEach(() => vi.clearAllMocks());

describe("Handheld Detector Sign-Out editor", () => {
  it("renders fixed D1-D9 rows with staff, area, supervisor, date, and clear controls", () => {
    render(<MemoryRouter><DetectorSignOutEditor workDate="2026-08-20" shift="D" record={record()} onRecordChange={vi.fn()} searchStaff={vi.fn().mockResolvedValue([])} /></MemoryRouter>);
    expect(screen.getAllByTestId("detector-signout-row").map((row) => within(row).getByRole("heading").textContent)).toEqual(["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"]);
    expect(screen.getByRole("combobox", { name: "D1 staff member" })).toBeInTheDocument();
    expect(screen.getByLabelText("D1 area of assignment")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Shift Supervisor" })).toBeInTheDocument();
    expect(screen.getByLabelText("Sign-out date")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Clear D1 row" })).toBeInTheDocument();
  });

  it("prevents duplicate unit codes and clears and saves a row", async () => {
    const duplicate = createEmptySignOutPayload("2026-08-20", "D"); duplicate.units[1].unit_code = "D1"; expect(() => parseSignOutPayload(duplicate)).toThrow(/D1|order|unit/i);
    const user = userEvent.setup(); const saved = record(); vi.mocked(paperworkApi.saveDailyRecord).mockResolvedValue(saved); const onRecordChange = vi.fn();
    render(<MemoryRouter><DetectorSignOutEditor workDate="2026-08-20" shift="D" record={record()} onRecordChange={onRecordChange} searchStaff={vi.fn().mockResolvedValue([])} /></MemoryRouter>);
    await user.type(screen.getByLabelText("D1 area of assignment"), "North Hall");
    await user.click(screen.getByRole("button", { name: "Clear D1 row" }));
    expect(screen.getByLabelText("D1 area of assignment")).toHaveValue("");
    await user.click(screen.getByRole("button", { name: "Save detector sign-out" }));
    await waitFor(() => expect(paperworkApi.saveDailyRecord).toHaveBeenCalled()); expect(onRecordChange).toHaveBeenCalledWith(saved);
  });

  it("offers preview and renders source-order signature-ready print rows", async () => {
    const user = userEvent.setup(); render(<MemoryRouter><DetectorSignOutEditor workDate="2026-08-20" shift="D" record={record()} onRecordChange={vi.fn()} searchStaff={vi.fn().mockResolvedValue([])} /></MemoryRouter>);
    await user.click(screen.getByRole("button", { name: "Preview" }));
    expect(screen.getByRole("dialog", { name: "Detector Sign-Out print preview" })).toBeInTheDocument();
    const print = screen.getAllByTestId("detector-signout-print").at(-1)!;
    expect(within(print).getAllByRole("row").slice(1).map((row) => within(row).getAllByRole("cell")[0].textContent)).toEqual(["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"]);
    expect(print).toHaveTextContent("Shift Supervisor"); expect(print).toHaveTextContent("Signature");
  });
});
